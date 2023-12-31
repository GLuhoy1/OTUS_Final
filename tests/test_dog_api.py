import allure
import pytest
import requests
import cerberus
import random
from urllib.parse import urlparse


BASE_URL = "https://dog.ceo/api/"
SHEMA_IMAGES = {
    "message": {
        "type": "list",
        "schema": {
            "type": "string",
            "regex": r"^https://images\.dog\.ceo/.+\.jpg$"
        }
    },
    "status": {"type": "string", "allowed": ["success"]}
}

SHEM_ALL_BREEDS = {
    "message": {
        "type": "dict",
        "valuesrules": {
            "type": "list",
            "schema": {"type": "string"}
        }
    },
    "status": {"type": "string"}
}

FALSE_SHEMA = {
    "status": {"type": "string", "allowed": ["error"]},
    "message": {"type": "string"},
    "code": {"type": "integer", "allowed": [404]}
}


# проверка формы JSON файла при запросе нескольких случайных изображений
@allure.epic("DOG API TESTS")
@allure.title("Random images")
@pytest.mark.parametrize("count", [30, 10, 2])
def test_random_images_structure(count):
    scheme_for_random_images = {
        "message": {"type": "list", "schema": {"type": "string"}},
        "status": {"type": "string", "allowed": ["success"]}
    }
    response = requests.get(f'{BASE_URL}breeds/image/random/{str(count)}')
    v = cerberus.Validator()
    assert response.status_code == 200
    assert v.validate(response.json(), scheme_for_random_images)


# Проверка выдачи рандомного изображения
@allure.epic("DOG API TESTS")
@allure.title("Random image")
def test_random_image():
    response = requests.get(f'{BASE_URL}breeds/image/random')
    assert response.status_code == 200
    assert response.json().get("message", "").lower().endswith(".jpg")


# проверка на факт выдачи сайтом при двух последовательных запросах несовпадающих изображений
@allure.epic("DOG API TESTS")
@allure.title("Is realy random images")
@pytest.mark.parametrize("iteration", range(1))
def test_really_random_image(iteration):
    first_response = requests.get(f'{BASE_URL}breeds/image/random')
    second_response = requests.get(f'{BASE_URL}breeds/image/random')
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["message"] != second_response.json()["message"]


# проверка соответствия формы списка всех пород
@allure.epic("DOG API TESTS")
@allure.title("check JSON structure of all breeds")
def test_breed_list_api_response():
    response = requests.get(f'{BASE_URL}breeds/list/all')
    v = cerberus.Validator()
    assert response.status_code == 200
    assert v.validate(response.json(), SHEM_ALL_BREEDS)


# фикстура создаёт словарь с породами у которых есть подпороды
@pytest.fixture(scope="module")
def breeds_with_subbreeds():
    response = requests.get(f"{BASE_URL}breeds/list/all")
    data = response.json()
    breeds_with_subbreeds = []
    for breed, subbreeds in data["message"].items():
        if subbreeds:
            breed_with_subbreeds = {
                "breed": breed,
                "subbreeds": subbreeds
            }
            breeds_with_subbreeds.append(breed_with_subbreeds)
    return breeds_with_subbreeds


# фикстура возвращает 5 случайных пород с подпородами
@pytest.fixture(params=[i for i in range(5)])
def random_breed_with_subbreed(breeds_with_subbreeds):
    breed_with_subbreeds = random.choice(breeds_with_subbreeds)
    return breed_with_subbreeds


# тест проверят соответствие списка подпород полученных разными способами
# по сути проверяет что при получении списков подпород 2 разными способами приходит одинаковы результат
# test for test
@allure.epic("DOG API TESTS")
@allure.title("Validation of sub-breed list from different sources ")
def test_compare_subbreeds(random_breed_with_subbreed, breeds_with_subbreeds):
    breed_name = random_breed_with_subbreed["breed"]
    expected_subbreeds = random_breed_with_subbreed["subbreeds"]
    url = f"{BASE_URL}breed/{breed_name}/list"
    response = requests.get(url)
    assert response.status_code == 200
    assert breed_name in [breed["breed"] for breed in breeds_with_subbreeds]
    assert set(expected_subbreeds) == set(response.json()["message"])


# фикстура создаёт список всех пород
@pytest.fixture(scope="module")
def all_breeds():
    response = requests.get(f"{BASE_URL}breeds/list/all")
    data = response.json()
    breeds = list(data["message"].keys())
    return breeds


# проверяет существование ссылки на картинку при запросе рандомного изображения
@allure.epic("DOG API TESTS")
@allure.title("Check the URL for random images")
@pytest.mark.parametrize("test_num", range(3))
def test_check_breed_image_existence(test_num, all_breeds):
    breed = random.choice(all_breeds)
    url = f"{BASE_URL}breed/{breed}/images/random"
    response = requests.get(url)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] is not None
    assert "breeds" in urlparse(data["message"]).path
    assert data["message"].endswith(".jpg")


# проверка изображений подпород
@allure.epic("DOG API TESTS")
@allure.title("Check images by subbreed")
@pytest.mark.parametrize("breed, subbreeds", [
    ("australian", ["shepherd"]),
    ("bulldog", ["boston", "english", "french"]),
    ("deerhound", ["scottish"]),
    ("elkhound", ["norwegian"]),
    ("ridgeback", ["rhodesian"])
])
def test_subreed_images(breed, subbreeds):
    for subreed in subbreeds:
        response = requests.get(f'{BASE_URL}breed/{breed}/{subreed}/images')
        assert response.status_code == 200
        v = cerberus.Validator()
        assert v.validate(response.json(), SHEMA_IMAGES)


@allure.epic("DOG API TESTS")
@allure.title("Check images by subbreed")
@pytest.mark.parametrize("breed", ["affenpinscher", "bullterrier", "deerhound", "dhole"])
def test_breed_random_images(breed):
    response = requests.get(f'{BASE_URL}breed/{breed}/images')
    assert response.status_code == 200
    v = cerberus.Validator()
    assert v.validate(response.json(), SHEMA_IMAGES)


@allure.epic("DOG API TESTS")
@allure.title("This test should be failure")
@pytest.mark.parametrize("false_url", [
    "breeds/list/false1",
    "breeds/list/false2",
    "breeds/list/false3"
])
# Проверка ответов при неправильных запросах
def test_failer(false_url):
    url = f'{BASE_URL}{false_url}'
    response = requests.get(url)
    assert response.status_code == 404
    response_json = response.json()
    v = cerberus.Validator()
    assert v.validate(response_json, FALSE_SHEMA), v.errors
