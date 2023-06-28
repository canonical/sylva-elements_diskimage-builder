#!/bin/bash

REPO_URL=${REPO_URL:-http://192.168.133.100/repository/kanod}
VERSION=${VERSION:-0.1.0}
ARTIFACT=${1:-core}

# shellcheck disable=SC2086
mvn ${MAVEN_CLI_OPTS} --batch-mode -B deploy:deploy-file ${MAVEN_OPTS} -DgroupId=kanod -DartifactId="${ARTIFACT}" -Dversion="${VERSION}" -Dpackaging=qcow2 -Dfile=img.qcow2 -Durl="${REPO_URL}" -DrepositoryId=kanod

