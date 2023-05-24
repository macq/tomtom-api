from tomtom_api.traffic_stats.models.responses import Sort


def test_from_dict():
    input_dict = {'sorted': True, 'unsorted': False, 'empty': False}
    truth = Sort(True, False, False)

    output = Sort.from_dict(input_dict)
    assert truth == output


def test_json_dataclass_sort():
    input_dict = {'sorted': True, 'unsorted': False, 'empty': False}
    truth = Sort(True, False, False)

    output = Sort.from_dict(input_dict)
    assert truth == output
