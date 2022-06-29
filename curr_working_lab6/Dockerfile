FROM centos7_cust_image:latest

###To "fix: UnicodeEncodeError: 'ascii' codec can't encode characters in position 0-8:" followed inst-->https://stackoverflow.com/questions/43356982/docker-python-set-utf-8-locale##################

ENV PYTHONIOENCODING=utf-8
ENV LC_ALL=en_CA.UTF-8
ENV LANG=en_CA.UTF-8
ENV LANGUAGE=en_CA.UTF-8

######To prevent "Failed to mount error!!!!"
VOLUME ["/sys/fs/cgroup", "/tmp", "/run", "/run/lock"]

###setting password for base centos7 image###########
RUN echo 'root:pass' | chpasswd

#####Setting working directory in container
WORKDIR /netauto

RUN yum -y install \
  python3-pip \
  python3

RUN python3 -m pip install -U pip
RUN python3 -m pip install -U setuptools

COPY requirements.txt .
RUN pip install docker
RUN pip3 install -r requirements.txt

###########"Juniper.roles" module dependencies##################
RUN ansible-galaxy install Juniper.junos
RUN ansible-galaxy collection install arista.eos
RUN ansible-galaxy collection install cisco.ios
RUN pip3 install junos-eznc
RUN pip3 install jxmlease

#############Copy project app into docker working directory and run#######
COPY netauto/ .
CMD ["python3","./main.py"]
