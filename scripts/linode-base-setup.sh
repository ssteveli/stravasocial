i#!/bin/bash
rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-7.noarch.rpm
yum install -y puppet git

git clone https://github.com/ssteveli/puppet.git /etc/puppet

puppet apply /etc/puppet/manifasts/site.pp --modulepath=/etc/puppet/modules

