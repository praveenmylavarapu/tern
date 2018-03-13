'''
Copyright (c) 2017 VMware, Inc. All Rights Reserved.
SPDX-License-Identifier: BSD-2-Clause
'''
import logging
import subprocess
import sys

from classes.docker_image import DockerImage
from classes.notice import Notice
from classes.layer import Layer
from classes.package import Package
from utils import dockerfile as df
from utils import container as cont
from utils import constants as const
from command_lib import command_lib as cmdlib
from report import errors
'''
Docker specific functions - used when trying to retrieve packages when
given a Dockerfile
'''

# dockerfile
dockerfile = ''
# dockerfile commands
docker_commands = []

# global logger
logger = logging.getLogger('ternlog')


def load_docker_commands(dockerfile_path):
    '''Given a dockerfile get a persistent list of docker commands'''
    global docker_commands
    docker_commands = df.get_directive_list(df.get_command_list(
        dockerfile_path))
    global dockerfile
    dockerfile = dockerfile_path


def print_dockerfile_base(base_instructions):
    '''For the purpose of tracking the lines in the dockerfile that
    produce packages, return a string containing the lines in the dockerfile
    that pertain to the base image'''
    base_instr = ''
    for instr in base_instructions:
        base_instr = base_instr + instr[0] + ' ' + instr[1] + '\n'
    return base_instr


def get_dockerfile_base():
    '''Get the base image object from the dockerfile base instructions
    1. get the instructions around FROM
    2. get the base image and tag
    3. Make notes based on what the image and tag rules are
    4. Return an image object'''
    try:
        base_instructions = df.get_base_instructions(docker_commands)
        base_image_tag = df.get_base_image_tag(base_instructions)
        # check for scratch
        if base_image_tag[0] == 'scratch':
            # there is no base image - return no image object
            return None
        # there should be some image object here
        repotag = base_image_tag[0] + df.tag_separator + base_image_tag[1]
        from_line = 'FROM ' + repotag
        origin = print_dockerfile_base(base_instructions)
        base_image = DockerImage(repotag)
        base_image.name = base_image_tag[0]
        # check if there is a tag
        if not base_image_tag[1]:
            message_string = errors.dockerfile_no_tag.format(
                dockerfile_line=from_line)
            no_tag_notice = Notice()
            no_tag_notice.origin = origin
            no_tag_notice.message = message_string
            no_tag_notice.level = 'warning'
            base_image.notices.add_notice(no_tag_notice)
            base_image.tag = 'latest'
        else:
            base_image.tag = base_image_tag[1]
        # check if the tag is 'latest'
        if base_image_tag[1] == 'latest':
            message_string = errors.dockerfile_using_latest.format(
                dockerfile_line=from_line)
            latest_tag_notice = Notice()
            latest_tag_notice.origin = origin
            no_tag_notice.message = message_string
            no_tag_notice.level = 'warning'
            base_image.notices.add_notice(latest_tag_notice)
        return base_image
    except ValueError as e:
        # needs logging
        print(e)
        return None


def check_base_image(image, tag):
    '''Given a base image object, check if an image exists
    If not then try to pull the image.'''
    image_tag_string = image + df.tag_separator + tag
    success = cont.check_image(image_tag_string)
    if not success:
        success = cont.pull_image(image_tag_string)
    return success

# REMOVE
def get_image_tag_string(image_tag_tuple):
    '''Given a tuple of the image and tag, return a string containing
    the image and tag'''
    return image_tag_tuple[0] + df.tag_separator + image_tag_tuple[1]


def get_dockerfile_image_tag():
    '''Return the image and tag used to build an image from the dockerfile'''
    image_tag_string = const.image + df.tag_separator + const.tag
    return image_tag_string


def is_build():
    '''Attempt to build a given dockerfile
    If it does not build return False. Else return True'''
    image_tag_string = get_dockerfile_image_tag()
    success = False
    msg = ''
    try:
        cont.build_container(dockerfile, image_tag_string)
    except subprocess.CalledProcessError as error:
        print(errors.docker_build_failed.format(
            dockerfile=dockerfile, error_msg=error.output))
        success = False
        msg = error.output
    else:
        success = True
    return success, msg

# LEFTOFF
def get_dockerfile_packages():
    '''Given the dockerfile commands get packages that may have been
    installed. Use this when there is no image or if it cannot be
    built
    1. For each RUN directive get the command used and the packages
    installed with it
    2. All of the packages that are recognized would be unconfirmed
    because there is no container to run the snippets against
    All the unrecognized commands will be returned as is
    Since there will be nothing more to do - recognized is just a list
    of packages that may have been installed in the dockerfile'''
    pkg_dict = cmds.remove_uninstalled(cmds.get_package_listing(
        docker_commands))
    recognized_list = []
    for command in pkg_dict['recognized'].keys():
        recognized_list.extend(pkg_dict['recognized'][command])
    pkg_dict.update({'recognized': recognized_list})
    return pkg_dict


