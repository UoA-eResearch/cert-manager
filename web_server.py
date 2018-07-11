#!/usr/bin/env python

from flask import Flask, render_template, request, send_file
import os
import subprocess
app = Flask(__name__, static_url_path='')

import uuid

@app.route('/', methods=['GET', 'POST'])
def root():
  if request.method == "GET":
    return render_template('index.html')
  elif request.method == "POST":
    print request.form
    f = request.form
    name = f["certificate_title"]
    safe_name = "".join(c for c in name if c.isalnum())
    badge_id = str(uuid.uuid4())
    cmd = ["create-certificate-template", "--issuer_name=" + f["issuer_name"], "--template_file_name=" + safe_name + ".json", "--certificate_title=" + name, "--criteria_narrative=" + f["criteria_narrative"], "--certificate_description=" + f["certificate_description"], "--badge_id=" + badge_id]
    os.chdir("../cert-tools")
    print(cmd)
    subprocess.call(cmd)
    f = request.files["roster"]
    rosterfile = "sample_data/rosters/roster_" + safe_name + ".csv"
    f.save(rosterfile)
    cmd = ["instantiate-certificate-batch", "--template_file_name=" + safe_name + ".json", "--roster=" + "rosters/roster_" + safe_name + ".csv"]
    subprocess.call(cmd)
    os.chdir("..")
    cmd = "cp cert-tools/sample_data/unsigned_certificates/" + safe_name + "* cert-issuer/conf/data/unsigned_certificates"
    subprocess.call(cmd, shell=True)
    subprocess.call("docker run --rm -v ~/cert-issuer/conf:/etc/cert-issuer bc/cert-issuer:1.0 cert-issuer -c /etc/cert-issuer/conf.ini; rm cert-issuer/conf/data/unsigned_certificates/*", shell=True)
    print("certs issued")
    os.chdir("cert-manager/zips/")
    subprocess.call("rm " + safe_name + ".zip; zip -j " + safe_name + ".zip ~/cert-issuer/conf/data/blockchain_certificates/" + safe_name + "*", shell=True)
    return send_file("zips/" + safe_name + ".zip", as_attachment=True)

if __name__ == '__main__':
  port = int(os.environ.get('PORT', 8080))
  app.run("0.0.0.0", port, debug=True)
