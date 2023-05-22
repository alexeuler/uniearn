#! /bin/bash

poetry run ansible-playbook -i inventory.yaml playbook.yaml $@