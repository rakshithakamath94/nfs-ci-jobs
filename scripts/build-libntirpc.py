#
# from: https://raw.githubusercontent.com/kbsingh/centos-ci-scripts/master/build_python_script.py
#
# This script uses the Duffy node management api to get fresh machines to run
# your CI tests on. Once allocated you will be able to ssh into that machine
# as the root user and setup the environ
#
# XXX: You need to add your own api key below, and also set the right cmd= line 
#      needed to run the tests
#
# Please note, this is a basic script, there is no error handling and there are
# no real tests for any exceptions. Patches welcome!

import json, urllib, subprocess, sys, os

url_base="http://admin.ci.centos.org:8080"
# we just build on CentOS-7/x86_64, CentOS-6 does not have 'mock'?
ver="7"
arch="x86_64"
count=1
script_url=os.getenv("TEST_SCRIPT")
templates_url=os.getenv("TEMPLATES_URL")

# read the API key for Duffy from the ~/duffy.key file
fo=open("/home/nfs-ganesha/duffy.key")
api=fo.read().strip()
fo.close()

# build the URL to request the system(s)
get_nodes_url="%s/Node/get?key=%s&ver=%s&arch=%s&count=%s" % (url_base,api,ver,arch,count)

# request the system
dat=urllib.urlopen(get_nodes_url).read()
b=json.loads(dat)

# create a rsync.passwd file on the reserved system to store RPMs on artifacts.ci.centos.org
cmd="cut -c1-13 < ~/duffy.key | ssh -t -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s 'cat > rsync.passwd ; chmod 0600 rsync.passwd'" % (b['hosts'][0])
rtn_code=subprocess.call(cmd, shell=True)

cmd="""ssh -t -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s '
	yum -y install curl &&
	curl -o build.sh %s &&
	CENTOS_VERSION="%s" CENTOS_ARCH="%s" TEMPLATES_URL="%s" bash build.sh'
""" % (b['hosts'][0], script_url, os.getenv("CENTOS_VERSION"), os.getenv("CENTOS_ARCH"), os.getenv("TEMPLATES_URL"))
rtn_code=subprocess.call(cmd, shell=True)

# copy the mock/resultdir logs for archiving as artifacts by the Jenkins job
if rtn_code != 0:
  resultdir="/srv/libntirpc/nightly/%s/%s" % (os.getenv("CENTOS_VERSION"), os.getenv("CENTOS_ARCH"))
  cmd="scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s:%s/*.log ." % (b['hosts'][0], resultdir)
  subprocess.call(cmd, shell=True)

# return the system(s) to duffy
done_nodes_url="%s/Node/done?key=%s&ssid=%s" % (url_base, api, b['ssid'])
das=urllib.urlopen(done_nodes_url).read()

sys.exit(rtn_code)
