#!/usr/bin/env bash
[[ ! ${WARDEN_DIR} ]] && >&2 echo -e "\033[31mThis script is not intended to be run directly!\033[0m" && exit 1

WARDEN_ENV_PATH="$(locateEnvPath)" || exit $?
loadEnvConfig "${WARDEN_ENV_PATH}" || exit $?
assertDockerRunning

set -a
export WARDEN_ENV_PATH
export WARDEN_ENV_TYPE
source ${WARDEN_ENV_PATH}/.env
set +a
${WARDEN_DIR}/commands/deploy.py "${WARDEN_PARAMS[0]:undefined}" "$@"
