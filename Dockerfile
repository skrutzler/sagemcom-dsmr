FROM python:3
RUN pip install pyserial && pip install cryptography && pip3 install pycryptodomex
RUN git clone https://github.com/skrutzler/sagemcom-dsmr.git

RUN pip3 install -r sagemcom-dsmr/pre-requirements.txt
RUN export CRYPTOGRAPHY_DONT_BUILD_RUST=1 && pip3 install -r sagemcom-dsmr/requirements.txt
ENTRYPOINT ["python3", "sagemcom-dsmr/serialToAPI.py"]