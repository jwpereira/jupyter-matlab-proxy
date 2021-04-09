import pytest, asyncio, secrets, datetime, random, json
from unittest.mock import patch
from jupyter_matlab_proxy import app
from jupyter_matlab_proxy.util import mw
from datetime import timezone
from jupyter_matlab_proxy.util import exceptions
from datetime import timedelta
from collections import namedtuple
from aioresponses import aioresponses
from aiohttp.http_exceptions import HttpProcessingError
"""This file tests methods present in jupyter_matlab_proxy/util/mw.py
"""



@pytest.fixture(name='mwa_api_data')
def mwa_api_data_fixture():
    """Pytest fixture which returns a namedtuple.
    
    The namedtuple contains values required for MW authentication

    Returns:
        namedtuple: A named tuple containing mwa, mhlm end-point URLs, source_id, identity_token, access_token and matlab_release.
    """

    mwa_api_endpoint = "https://login.mathworks.com/authenticationws/service/v4"
    mhlm_api_endpoint = "https://licensing.mathworks.com/mls/service/v1/entitlement/list",
    identity_token = secrets.token_urlsafe(324)
    source_id = secrets.token_urlsafe(21)
    access_token = secrets.token_urlsafe(22)
    matlab_release='R2020b'

    mwa_api_variables = namedtuple('mwa_api_variables', [
        'mwa_api_endpoint', 'mhlm_api_endpoint', 'identity_token', 'source_id', 'access_token', 'matlab_release'
    ])

    variables = mwa_api_variables(mwa_api_endpoint, mhlm_api_endpoint,
                                  identity_token, source_id, access_token, matlab_release)

    return variables


@pytest.fixture(name='fetch_access_token_valid_json')
def fetch_access_token_valid_json_fixture():
    """Pytest fixture which returns a dict.
    
    This fixture returns a dict representing a valid json response from mhlm servers.
    
    Returns:
        dict : A dictionary containing Key-value pairs present in a valid json response from mhlm servers.
    """

    now = datetime.datetime.now(timezone.utc)
    authentication_date = str(now.strftime("%Y-%m-%dT%H:%M:%S.%f%z"))
    expiration_date = str(
        (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"))

    login_identifier = "abc@mathworks.com"
    reference_ID = int(''.join([str(random.randint(0, 10)) for _ in range(8)]))

    first_name = "abc"
    last_name = "def"
    user_id = int(''.join([str(random.randint(0, 10)) for _ in range(13)]))

    access_token_string = int(''.join(
        [str(random.randint(0, 10)) for _ in range(272)]))

    json_data = {
        "authenticationDate": authentication_date,
        "expirationDate": expiration_date,
        "id": 0,
        "loginIdentifier": login_identifier,
        "loginIdentifierType": "MWAS",
        "referenceDetail": {
            "referenceId": str(reference_ID),
            "country": "IN",
            "email": login_identifier,
            "firstName": first_name,
            "lastName": last_name,
            "displayName": first_name,
            "sector": "None",
            "userId": "mwa" + str(user_id),
            "profilePicture": "https://www.mathworks.com/"
        },
        "referenceId": str(reference_ID),
        "referenceType": "WEBPROFILEID",
        "source": "desktop-jupyter",
        "accessTokenString": str(access_token_string)
    }

    return json_data


@pytest.fixture(name='mock_response')
def mock_aiohttp_client_session():
    """A pytest fixture which yields an aioresponses() object

    Yields:
       aioresponses : An aioresponses() object which mocks the HTTP Response object. 
    """
    with aioresponses() as m:
        yield m

async def test_fetch_access_token(mwa_api_data,
                                  fetch_access_token_valid_json, mock_response):
    """Test to check mw.fetch_access_token method returns valid json response. 
    
    The mock_response fixture mocks the aiohttp.ClientSession().post() method to return a custom HTTP response.

    Args:
        mwa_api_data (namedtuple): A pytest fixture which returns a namedtuple containing values for MW servers.
        fetch_access_token_valid_json (Dict): A pytest fixture which returns a dict representing a valid json response.
        mock_response: Pytest fixture which yields a aioresponses() object for mocking HTTP response
    """    
    json_data = fetch_access_token_valid_json
    
    url =  f"{mwa_api_data.mwa_api_endpoint}/tokens/access?tokenString={mwa_api_data.identity_token}&type=MWAS&sourceId={mwa_api_data.source_id}"    
    payload = dict(accessTokenString=json_data['accessTokenString'])
    
    
    mock_response.post(url, payload=payload)    
        

    resp = await mw.fetch_access_token(mwa_api_data.mwa_api_endpoint,
                                       mwa_api_data.identity_token,
                                       mwa_api_data.source_id)
    

    assert json_data["accessTokenString"] == resp["token"]
    
    

async def test_fetch_access_token_licensing_error(mwa_api_data, mock_response):
    """Test to check mw.fetch_access_token() method raises a exceptions.OnlineLicensingError.

    When an invalid response is received from the server, this test checks if exceptions.OnlineLicensingError is raised.
    Args:
        mock_response: Pytest fixture which yields a aioresponses() object for mocking HTTP response
        mwa_api_data (namedtuple): A pytest fixture which returns a namedtuple containing values for MW authentication
    """
        
    url =  f"{mwa_api_data.mwa_api_endpoint}/tokens/access?tokenString={mwa_api_data.identity_token}&type=MWAS&sourceId={mwa_api_data.source_id}"    
      
    
    mock_response.post(url, exception=exceptions.OnlineLicensingError('Communication failed')) 

    with pytest.raises(exceptions.OnlineLicensingError):        
        resp = await mw.fetch_access_token(mwa_api_data.mwa_api_endpoint,
                                            mwa_api_data.identity_token,
                                            mwa_api_data.source_id)
        
       


async def test_fetch_expand_token_licensing_error(mock_response, mwa_api_data):
    """Test to check fetch_expand_token raises exceptions.OnlineLicensing error.

    Args:
        mock_response: Pytest fixture which yields a aioresponses() object for mocking HTTP response
        mwa_api_data (namedtuple): A pytest fixture which returns a namedtuple containing values for MW authentication
    """  
    url=  f"{mwa_api_data.mwa_api_endpoint}/tokens?tokenString={mwa_api_data.identity_token}&tokenPolicyName=R1&sourceId={mwa_api_data.source_id}"
    
    mock_response.post(url, exception=exceptions.OnlineLicensingError('Communication failed'))
    with pytest.raises(exceptions.OnlineLicensingError):
        resp = await mw.fetch_expand_token(mwa_api_data.mwa_api_endpoint,
                                           mwa_api_data.identity_token,
                                           mwa_api_data.source_id)


@pytest.fixture(name='fetch_expand_token_valid_json')
def fetch_expand_token_valid_json_fixture():
    """Pytest fixture which returns a dict
    
    The return value represents a valid json response when mw.fetch_expand_token function is called.

    Returns:
        dict: A dict representing valid json response.
    """
    now = datetime.datetime.now(timezone.utc)
    expiration_date = str(
        (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"))
    first_name = "abc"
    display_name = first_name
    last_name = "def"
    reference_ID = int(''.join([str(random.randint(0, 10)) for _ in range(8)]))
    user_id = int(''.join([str(random.randint(0, 10)) for _ in range(13)]))

    json_data = {
        "expirationDate": str(expiration_date),
        "referenceDetail": {
            "referenceId": str(reference_ID),
            "firstName": first_name,
            "lastName": last_name,
            "displayName": first_name,
            "userId": "mwa" + str(user_id),
        },
    }

    return json_data


async def test_fetch_expand_token(mock_response, fetch_expand_token_valid_json,
                                  mwa_api_data):
    """Test to check if mw.fetch_expand_token returns a correct json response
    
    mock_response is used to mock ClientSession.post method to return a HTTP Response containing a valid json response.
    Args:
        mock_response: Pytest fixture which yields a aioresponses() object for mocking HTTP response
        fetch_expand_token_valid_json (namedtuple): Pytest fixture which returns a dict which is returned by the server when no exception is raised.
        mwa_api_data (namedtuple): A namedtuple which contains info related to mwa.
    """
    json_data = fetch_expand_token_valid_json
    url=  f"{mwa_api_data.mwa_api_endpoint}/tokens?tokenString={mwa_api_data.identity_token}&tokenPolicyName=R1&sourceId={mwa_api_data.source_id}"
    
    
    referenceDetail = dict(firstName=json_data['referenceDetail']['firstName'],
                           lastName=json_data['referenceDetail']['lastName'],
                           displayName= json_data['referenceDetail']['displayName'],
                           userId=json_data['referenceDetail']['userId'],
                           referenceId=json_data['referenceDetail']['referenceId'])
    
    payload = dict(expirationDate=json_data['expirationDate'],
                   referenceDetail=referenceDetail)
                   
    
    mock_response.post(url, payload=payload)
    
    resp = await mw.fetch_expand_token(mwa_api_data.mwa_api_endpoint,
                                       mwa_api_data.identity_token,
                                       mwa_api_data.source_id)

    assert resp is not None and len(resp.keys()) > 0


async def test_fetch_entitlements_licensing_error(mock_response, mwa_api_data):
    """Test to check if fetch_entitlements raises exceptions.OnlineLicensingError.

    When an invalid response is received, this test checks if exceptions.OnlineLicenseError is raised.
    
    Args:        
        mock_response: Pytest fixture which yields a aioresponses() object for mocking HTTP response
        mwa_api_data (namedtuple): A namedtuple which contains info related to mwa.
    """
    url = f"{mwa_api_data.mhlm_api_endpoint}?token={mwa_api_data.access_token}&release={mwa_api_data.matlab_release}&coreProduct=ML&context=jupyter&excludeExpired=true"

    mock_response.post(url, exception=exceptions.OnlineLicensingError('Communication Error'))

    with pytest.raises(exceptions.OnlineLicensingError):
        resp = await mw.fetch_entitlements(mwa_api_data.mhlm_api_endpoint,
                                           mwa_api_data.access_token,
                                           mwa_api_data.matlab_release)


@pytest.fixture(name='invalid_entitlements',
                params=[
                    """<?xml version="1.0" encoding="UTF-8"?>
                        <describe_entitlements_response>
                        </describe_entitlements_response>""",
                    """<?xml version="1.0" encoding="UTF-8"?>
                        <describe_entitlements_response>
                            <entitlements>
                            </entitlements>
                        </describe_entitlements_response>"""
                ],
                ids=[
                    "Invalid Entitlement : No entitlements tag",
                    "Invalid Entitlement : Empty entitlements tag"
                ])
def invalid_entitlements_fixture(request):
    """A parameterized pytest fixture which returns invalid entitlements.
      
    
    Args:
        request : Built-in pytest fixture

    Returns:
        [String]: A string containing invalid Entitlements.
    """
    return request.param


async def test_fetch_entitlements_entitlement_error(mock_response, mwa_api_data,
                                                    invalid_entitlements):
    """Test to check fetch_entitlements raises exceptions.EntitlementError. 
    
    
    When invalid entitlements are received as a response, this test checks if mw.fetch_entitlements raises an
    exceptions.EntitlementError. mock_response mocks aiohttp.ClientSession.post method to send invalid entitlements as a HTTP response.

    Args:
      
        mock_response: Pytest fixture which yields a aioresponses() object for mocking HTTP response
        mwa_api_data (namedtuple): A namedtuple which contains info related to mwa.
        invalid_entitlements (String): String containing invalid entitlements
    """    
    url = f"{mwa_api_data.mhlm_api_endpoint}?token={mwa_api_data.access_token}&release={mwa_api_data.matlab_release}&coreProduct=ML&context=jupyter&excludeExpired=true"

    mock_response.post(url, body=invalid_entitlements)

    with pytest.raises(exceptions.EntitlementError):
        resp = await mw.fetch_entitlements(mwa_api_data.mhlm_api_endpoint,
                                           mwa_api_data.access_token,
                                           mwa_api_data.matlab_release)


@pytest.fixture(name='valid_entitlements')
def valid_entitlements_fixture():
    """
        Pytest fixture which returns a string representing valid entitlements
    """
    id = int(''.join([str(random.randint(0, 10)) for _ in range(7)]))
    license_number = int(''.join(
        [str(random.randint(0, 10)) for _ in range(8)]))

    return """<?xml version="1.0" encoding="UTF-8"?>
                <describe_entitlements_response>
                <entitlements>
                    <entitlement>
                        <id>%d</id>
                        <label>MATLAB</label>
                        <license_number>%d</license_number>
                        </entitlement>
                </entitlements>
                </describe_entitlements_response>""" % (id, license_number)


async def test_fetch_entitlements(mock_response, mwa_api_data, valid_entitlements):
    """Test to check test_fetch_entitlements returns valid response.
    
    
    mock_response mocks aiohttpClientSession.post() method  to return valid entitlements as a HTTP response
    Args:
        mock_response: Pytest fixture which yields a aioresponses() object for mocking HTTP response
        mwa_api_data (namedtuple): A namedtuple which contains info related to mwa.
        valid_entitlements (String): String containing valid entitlements as a response.
    """
    
    url = f"{mwa_api_data.mhlm_api_endpoint}?token={mwa_api_data.access_token}&release={mwa_api_data.matlab_release}&coreProduct=ML&context=jupyter&excludeExpired=true"

    mock_response.post(url, body=valid_entitlements)

   
    resp = await mw.fetch_entitlements(mwa_api_data.mhlm_api_endpoint,
                                        mwa_api_data.access_token,
                                        mwa_api_data.matlab_release)


    assert resp is not None and len(resp) > 0


def test_parse_mhlm_no_error():
    """Test to check mw.parse_mhlm_error() method returns none when no mhlm specific error
    is present in the logs.
    """
    logs = ["Starting MATLAB proxy-app", "Error parsing config, resetting."]

    actual_output = mw.parse_mhlm_error(logs)
    expected_output = None

    assert actual_output == expected_output


def test_parse_mhlm_error():
    """Test to check mw.parse_mhlm_error() returns an exceptions.OnlineLiceningError. 
    
    When logs contain mhlm specific error information, this test checks if exceptions.OnlineLicensingError is raised.
    """
    logs = ["License Manager Error", "MHLM Licensing Failed"]
    actual_output = mw.parse_mhlm_error(logs)
    expected_output = exceptions.OnlineLicensingError

    assert isinstance(actual_output, expected_output)


def test_parse_nlm_no_error():
    """Test to check parse_nlm_error returns none when no nlm specific error information is present in logs.
    """
    logs = []
    conn_str = ""
    expected_output = None

    assert mw.parse_nlm_error(logs, conn_str) == expected_output


def test_parse_nlm_error():
    """Test to check parse_nlm_error() method returns an exception when logs contain an error.
    
    When logs contain nlm specific errors, this test checks if parse_nlm_error() raises exceptions.NetworkLicensingError.
    """
    logs = [
        "Starting MATLAB proxy-app", "License checkout failed",
        "Error parsing config, resetting.", "Diagnostic Information"
    ]

    conn_str = "abc@nlm"

    actual_output = mw.parse_nlm_error(logs, conn_str)
    expected_output = exceptions.NetworkLicensingError

    assert isinstance(actual_output, expected_output)


def test_parse_other_error():
    """This test checks if exception.MatlabError is raised when matlab processes returncode is not 0 and logs contain
    matlab specific information
    """
    logs = ["Starting MATLAB proxy-app", "Error parsing config, resetting."]

    expected_output = exceptions.MatlabError
    actual_output = mw.parse_other_error(logs)

    assert isinstance(actual_output, expected_output)