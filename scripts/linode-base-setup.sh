#!/bin/bash
rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-7.noarch.rpm
yum update -y
yum install -y puppet git

git clone https://github.com/ssteveli/puppet.git /opt/puppet

puppet apply /opt/puppet/manifasts/site.pp --modulepath=/opt/puppet/modules

