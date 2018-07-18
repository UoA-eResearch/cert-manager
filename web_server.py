#!/usr/bin/env python

from flask import Flask, render_template, request, send_file
import os
import subprocess
app = Flask(__name__, static_url_path='')

import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import csv

import sys
reload(sys)  # Reload is a hack
sys.setdefaultencoding('UTF8')

def make_safe(string):
  return "".join(char for char in string if char.isalnum())

@app.route('/', methods=['GET', 'POST'])
def root():
  if request.method == "GET":
    return render_template('index.html')
  elif request.method == "POST":
    print(request.form)
    f = request.form

    name = f["certificate_title"]
    safe_name = make_safe(name)
    badge_id = str(uuid.uuid4())
    cmd = ["create-certificate-template", "--issuer_name=" + f["issuer_name"], "--template_file_name=" + safe_name + ".json", "--certificate_title=" + name, "--criteria_narrative=" + f["criteria_narrative"], "--certificate_description=" + f["certificate_description"], "--badge_id=" + badge_id]
    os.chdir(os.path.expanduser("~/cert-tools"))
    print(cmd)
    subprocess.call(cmd)
    rosterf = request.files["roster"]
    rosterfile = "sample_data/rosters/roster_" + safe_name + ".csv"
    rosterf.save(rosterfile)
    cmd = ["instantiate-certificate-batch", "--template_file_name=" + safe_name + ".json", "--roster=" + "rosters/roster_" + safe_name + ".csv"]
    subprocess.call(cmd)
    os.chdir(os.path.expanduser("~"))
    cmd = "cp cert-tools/sample_data/unsigned_certificates/" + safe_name + "* cert-issuer/conf/data/unsigned_certificates"
    subprocess.call(cmd, shell=True)
    subprocess.call("docker run --rm -v ~/cert-issuer/conf:/etc/cert-issuer bc/cert-issuer:1.0 cert-issuer -c /etc/cert-issuer/conf.ini; rm cert-issuer/conf/data/unsigned_certificates/*;docker restart certviewer_web_1", shell=True)
    print("certs issued")

    if f.get("sendmail"):
      print("Sending mail!")
      rosterf.seek(0)
      reader = list(csv.DictReader(rosterf))
      print("{} recipients".format(len(reader)))
      fromaddr = f["sending_address"]
      body_template = f["sending_body"]
      subject = f["sending_subject"]
      server = smtplib.SMTP('mailhost.auckland.ac.nz')
      for row in reader:
        toaddr = row["identity"]
        filename = make_safe(f["certificate_title"] + toaddr)
        url = "https://blockcert.auckland.ac.nz/" + filename
        body = body_template.replace("ISSUER_NAME", f["issuer_name"]).replace("CERTIFICATE_TITLE", f["certificate_title"]).replace("CERTIFICATE_DESCRIPTION", f["certificate_description"]).replace("VIEW_URL", url).replace("NAME", row["name"])
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = fromaddr
        msg['To'] = toaddr
        part1 = MIMEText(body, 'html', 'utf-8')
        msg.attach(part1)
        print("Sending mail from " + fromaddr + " to " + toaddr + " with msg " + msg.as_string())
        server.sendmail(fromaddr, toaddr, msg.as_string())
      server.quit()

    os.chdir(os.path.expanduser("~/cert-manager/zips/"))
    subprocess.call("rm " + safe_name + ".zip; zip -j " + safe_name + ".zip ~/cert-issuer/conf/data/blockchain_certificates/" + safe_name + "*", shell=True)
    return send_file("zips/" + safe_name + ".zip", as_attachment=True)

if __name__ == '__main__':
  port = int(os.environ.get('PORT', 8080))
  app.run("0.0.0.0", port, debug=False)
