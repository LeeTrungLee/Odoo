FROM odoo:19

COPY ./config/requirements.txt /tmp/requirements.txt

RUN if [ -s /tmp/requirements.txt ]; then pip3 install -r /tmp/requirements.txt; fi