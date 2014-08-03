#!/bin/bash
rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-7.noarch.rpm
rpm -ivh http://dl.fedoraproject.org/pub/epel/beta/7/x86_64/epel-release-7-0.2.noarch.rpm

yum update -y
yum install -y puppet git

if [ ! -d "/opt/puppet" ]; then
	git clone https://github.com/ssteveli/puppet.git /opt/puppet
else
	cd /opt/puppet; git pull
fi

if [ ! -d "/opt/puppet/modules/firewall" ]; then
	git clone https://github.com/puppetlabs/puppetlabs-firewall.git /opt/puppet/modules/firewall
else
	cd /opt/puppet/modules; git pull
fi

# get fresh configuration
if [ -d "/opt/puppet/hieradata" ]; then
	rm -rf /opt/puppet/hieradata
fi

mkdir -p /opt/puppet/hieradata
wget \
	--header="Authorization: token $GITHUB_ACCESS_TOKEN" \
	-O /tmp/config.tar.gz \
	https://api.github.com/repos/ssteveli/puppet.private/tarball/master
tar xvf /tmp/config.tar.gz --strip-components=2 -C /opt/puppet/hieradata ssteveli-puppet.private-*/strava-compare
	
puppet apply /opt/puppet/manifasts/site.pp --modulepath=/opt/puppet/modules > /tmp/puppet.log 2>&1

