FROM dockerfile/python

RUN pip install flask
RUN pip install pymongo
RUN pip install gearman

CMD cd /data/stravasocial/api; python /data/stravasocial/api/api.py
