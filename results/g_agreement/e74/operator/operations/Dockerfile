# This local alias is checked against the exact parent config ID before build.
FROM codex/e74-science-447fe082:locked
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1
WORKDIR /opt/e74-ops
COPY OS_LOCK.json SCIENTIFIC_FILES.json start.py sshd_config verify_ops.py ./
COPY debs/ /tmp/e74-debs/
RUN python -c 'import json,hashlib,pathlib; d=json.load(open("OS_LOCK.json")); assert all(hashlib.sha256((pathlib.Path("/tmp/e74-debs")/p["filename"]).read_bytes()).hexdigest()==p["sha256"] for p in d["packages"])' \
 && printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d \
 && chmod 755 /usr/sbin/policy-rc.d \
 && apt-get --no-install-recommends -y install /tmp/e74-debs/*.deb \
 && rm -f /etc/ssh/ssh_host_*key* \
 && rm -rf /tmp/e74-debs /var/lib/apt/lists/* \
 && python verify_ops.py > /CPU_OPERATIONS_RECEIPT.json
EXPOSE 22
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "python", "/opt/e74-ops/start.py"]
