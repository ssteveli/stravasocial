#!/bin/bash
rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-7.noarch.rpm
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

puppet apply /opt/puppet/manifasts/site.pp --modulepath=/opt/puppet/modules

