#!/usr/bin/env python

from flask import Flask, render_template, request
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
    badge_id = str(uuid.uuid4())
    cmd = ["create-certificate-template", "--issuer_name=" + name, "--template_file_name=" + name + ".json", "--certificate_title=" + name, "--criteria_narrative=" + f["criteria_narrative"], "--certificate_description=" + f["certificate_description"], "--badge_id=" + badge_id]
    os.chdir("../cert-tools")
    print(cmd)
    subprocess.call(cmd)
    f = request.files["roster"]
    f.save("sample_data/rosters/roster_" + name + ".csv")
    return "OK!"

if __name__ == '__main__':
  port = int(os.environ.get('PORT', 8080))
  app.run("0.0.0.0", port, debug=True)
