FROM dockerfile/python

RUN wget -O /tmp/requirements.txt https://raw.githubusercontent.com/ssteveli/stravasocial/master/app/api/requirements.txt
RUN pip install -r /tmp/requirements.txt

CMD cd /data/stravasocial/app/api; python /data/stravasocial/api/app/api.py
