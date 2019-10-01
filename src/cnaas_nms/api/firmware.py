import os
import json
import requests
import yaml

from flask import request
from flask_restful import Resource
from cnaas_nms.scheduler.scheduler import Scheduler
from cnaas_nms.api.generic import empty_result
from cnaas_nms.scheduler.wrapper import job_wrapper
from cnaas_nms.tools.log import get_logger
from cnaas_nms.tools.get_apidata import get_apidata

logger = get_logger()


def httpd_url() -> str:
    apidata = get_apidata()
    httpd_url = 'https://cnaas_httpd/api/v1.0/'
    if isinstance(apidata, dict) and 'httpd_url' in apidata:
        httpd_url = apidata['httpd_url']
    return httpd_url


def verify_tls() -> bool:
    verify_tls = True
    apidata = get_apidata()
    if isinstance(apidata, dict) and 'verify_tls' in apidata:
        verify_tls = apidata['verify_tls']
    return verify_tls


@job_wrapper
def get_firmware(**kwargs: dict) -> str:
    try:
        res = requests.post(httpd_url(), json=kwargs,
                            verify=verify_tls())
        json_data = json.loads(res.content)
    except Exception as e:
        logger.exception(f"Exception while getting firmware: {e}")
        return 'Could not download firmware: ' + str(e)
    if json_data['status'] == 'error':
        return json_data['message']
    return 'File downloaded from: ' + kwargs['url']


@job_wrapper
def get_firmware_chksum(**kwargs: dict) -> str:
    try:
        url = httpd_url() + '/' + kwargs['filename']
        res = requests.get(url, verify=verify_tls())
        json_data = json.loads(res.content)
    except Exception as e:
        logger.exception(f"Exceptionb while getting checksum: {e}")
        return 'Failed to get checksum for ' + kwargs['filename']
    if json_data['status'] == 'error':
        return json_data['message']
    return json_data['data']['file']['sha1']


@job_wrapper
def remove_file(**kwargs: dict) -> str:
    try:
        url = httpd_url() + '/' + kwargs['filename']
        res = requests.delete(url, verify=verify_tls())
        json_data = json.loads(res.content)
    except Exception as e:
        logger.exception(f"Exception when removing firmware: {e}")
        return 'Failed to remove file'
    if json_data['status'] == 'error':
        return 'Failed to remove file ' + kwargs['filename']
    return 'File ' + kwargs['filename'] + ' removed'


class FirmwareApi(Resource):
    def post(self) -> dict:
        json_data = request.get_json()
        scheduler = Scheduler()
        job_id = scheduler.add_onetime_job(
            'cnaas_nms.api.firmware:get_firmware',
            when=1,
            kwargs=json_data)
        res = empty_result(data='Scheduled job to download firmware')
        res['job_id'] = job_id

        return res

    def get(self) -> dict:
        try:
            res = requests.get(httpd_url() + 'firmware',
                               verify=verify_tls())
            json_data = json.loads(res.content)
        except Exception as e:
            logger.exception(f"Exception when getting images: {e}")
            return empty_result(status='error',
                                data='Could not get files'), 404
        return empty_result(status='success', data=json_data)


class FirmwareImageApi(Resource):
    def get(self, filename: str) -> dict:
        scheduler = Scheduler()
        job_id = scheduler.add_onetime_job(
            'cnaas_nms.api.firmware:get_firmware_chksum',
            when=1,
            kwargs={'filename': filename})
        res = empty_result(data='Scheduled job get firmware information')
        res['job_id'] = job_id

        return res

    def delete(self, filename: str) -> dict:
        scheduler = Scheduler()
        job_id = scheduler.add_onetime_job(
            'cnaas_nms.api.firmware:remove_file',
            when=1,
            kwargs={'filename': filename})
        res = empty_result(data='Scheduled job to remove firmware')
        res['job_id'] = job_id

        return res
