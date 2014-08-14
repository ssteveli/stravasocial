FROM dockerfile/python

RUN wget -O /tmp/requirements.txt https://raw.githubusercontent.com/ssteveli/stravasocial/adding_strava_caching/app/api/requirements.txt
RUN pip install -r /tmp/requirements.txt

RUN cd /tmp; git clone https://github.com/ssteveli/stravalib.git
RUN cd /tmp/stravalib; python setup.py install

ENV PYTHONPATH /data/stravasocial/app
CMD python /data/stravasocial/app/api/api.py
