#!/usr/bin/env python3

from flask import Flask, render_template, request, send_file, send_from_directory, abort
import os
import subprocess
app = Flask(__name__, static_url_path='')

import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd

@app.route('/images/<path:path>')
def send_image(path):
    return send_from_directory('templates/images', path)

def make_safe(string):
  return "".join(char for char in string if char.isalnum())

@app.route('/', methods=['GET', 'POST'])
def root():
  if request.method == "GET":
    return render_template('index.html')
  elif request.method == "POST":
    print(request.form)
    f = request.form
    os.chdir(os.path.expanduser("~/cert-tools"))

    name = f["certificate_title"]
    safe_name = make_safe(name)
    badge_id = str(uuid.uuid4())
    cmd = [ "create-certificate-template",
            "--issuer_name=" + f["issuer_name"],
            "--template_file_name=" + safe_name + ".json",
            "--certificate_title=" + name,
            "--criteria_narrative=" + f["criteria_narrative"],
            "--certificate_description=" + f["certificate_description"],
            "--badge_id=" + badge_id,
    ]

    issuer_logo_file = request.files.get("issuer_logo_file")
    if issuer_logo_file:
      issuer_logo_filename = "images/" + safe_name + "_" + issuer_logo_file.filename
      issuer_logo_file.save("sample_data/" + issuer_logo_filename)
      cmd.append("--issuer_logo_file=" + issuer_logo_filename)
    cert_image_file = request.files.get("cert_image_file")
    if cert_image_file:
      cert_image_file_filename = "images/" + safe_name + "_" + cert_image_file.filename
      cert_image_file.save("sample_data/" + cert_image_file_filename)
      cmd.append("--cert_image_file=" + cert_image_file_filename)

    print(" ".join(cmd))
    subprocess.call(cmd)
    rosterf = request.files["roster"]
    rosterfile = "sample_data/rosters/roster_" + safe_name + ".csv"
    
    roster = pd.read_csv(rosterf)
    roster.columns = roster.columns.str.strip()
    print(roster)
    if len(roster) == 0:
      abort(400, "The csv file must contain at least one row")
    if not all(k in roster.keys() for k in ["name", "pubkey", "identity"]):
      abort(400, 'The csv file must contain name, pubkey, and identity')
    for i in range(len(roster)):
      if ":" not in roster.pubkey[i]:
        roster.pubkey[i] = "ID:" + roster.pubkey[i]
    roster[["name", "pubkey", "identity"]].to_csv(rosterfile, index=False)

    cmd = ["instantiate-certificate-batch", "--template_file_name=" + safe_name + ".json", "--roster=" + "rosters/roster_" + safe_name + ".csv"]
    print(" ".join(cmd))
    subprocess.call(cmd)
    os.chdir(os.path.expanduser("~"))
    cmd = "cp cert-tools/sample_data/unsigned_certificates/" + safe_name + "* cert-issuer/conf/data/unsigned_certificates"
    subprocess.call(cmd, shell=True)
    subprocess.call("docker run --rm -v ~/cert-issuer/conf:/etc/cert-issuer bc/cert-issuer:1.0 cert-issuer -c /etc/cert-issuer/conf.ini; rm cert-issuer/conf/data/unsigned_certificates/*;docker restart cert-viewer_web_1", shell=True)
    print("certs issued")

    if f.get("sendmail"):
      print("Sending mail!")
      print("{} recipients".format(len(roster)))
      fromaddr = f["sending_address"]
      cc = f["sending_cc"]
      bcc = f["sending_bcc"]
      body_template = f["sending_body"]
      subject = f["sending_subject"]
      server = smtplib.SMTP('mailhost.auckland.ac.nz')
      for i, row in roster.iterrows():
        toaddr = row["identity"]
        filename = make_safe(f["certificate_title"] + toaddr)
        url = "https://blockcert.auckland.ac.nz/" + filename
        name = row.get("firstname") or row.get("name")
        body = body_template.replace("ISSUER_NAME", f["issuer_name"]).replace("CERTIFICATE_TITLE", f["certificate_title"]).replace("CERTIFICATE_DESCRIPTION", f["certificate_description"]).replace("VIEW_URL", url).replace("FIRSTNAME", name).replace("NAME", name)
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['CC'] = cc
        part1 = MIMEText(body, 'html', 'utf-8')
        msg.attach(part1)
        print("Sending mail from " + fromaddr + " to " + toaddr + " with msg " + msg.as_string())
        toaddrs = [toaddr] + cc.split(",") + bcc.split(",")
        server.sendmail(fromaddr, toaddrs, msg.as_string())
      server.quit()

    os.chdir(os.path.expanduser("~/cert-manager/zips/"))
    subprocess.call("rm " + safe_name + ".zip; zip -j " + safe_name + ".zip ~/cert-issuer/conf/data/blockchain_certificates/" + safe_name + "*", shell=True)
    return send_file("zips/" + safe_name + ".zip", as_attachment=True)

if __name__ == '__main__':
  port = int(os.environ.get('PORT', 8080))
  app.run("0.0.0.0", port, debug=False)
