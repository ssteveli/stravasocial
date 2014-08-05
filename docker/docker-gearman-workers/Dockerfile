FROM dockerfile/python

RUN wget -O /tmp/requirements.txt https://raw.githubusercontent.com/ssteveli/stravasocial/master/app/loader/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN cd /tmp; git clone https://github.com/ssteveli/stravalib.git
RUN cd /tmp/stravalib; python setup.py install

CMD cd /data/stravasocial/app; python loader/StravaCompareWorker.py

