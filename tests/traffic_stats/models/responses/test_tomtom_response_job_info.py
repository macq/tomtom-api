from tomtom_api.traffic_stats.models.responses import TomtomResponseStatus
from tomtom_api.traffic_stats.models.status import TomtomJobState
def test_convert_from_dict():
    input_dict = {'jobId': "678", "jobState": "DONE", "responseStatus": "ok"}
    truth = TomtomResponseStatus(678, TomtomJobState.DONE, 'ok')

    output = TomtomResponseStatus.from_dict(input_dict)
    assert truth == output