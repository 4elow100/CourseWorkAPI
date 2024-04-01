import requests
import json
from classes import VKAPI
import os
import shutil

profiles = {}
trigger = True
count = 0


def print_albums_input(albums: dict):
    album_print = 'Выберите альбом для сохранения из него фото на Яндекс.Диск:'
    for album in albums['items']:
        if album['id'] == -6:
            album_print = (f'{album_print}\n'
                           f'{albums["items"].index(album) + 1} - Фотографии профиля ({album["size"]} шт.)')
        elif album['id'] == -7:
            album_print = (f'{album_print}\n'
                           f'{albums["items"].index(album) + 1} - Фотографии со стены ({album["size"]} шт.)')
        else:
            album_print = (f'{album_print}\n'
                           f'{albums["items"].index(album) + 1} - {album["title"]} ({album["size"]} шт.)')
    return album_print


def error_msg_vk(code: int) -> str:
    if code == 1:
        return 'Неизвестная ошибка. Попробуйте повторить позже'
    elif code == 10:
        return 'Внутренняя ошибка сервера. Попробуйте повторить позже'
    elif code == 18:
        return 'Страница выбранного пользователя удалена или заблокирована'
    elif code == 30:
        return 'Профиль выбранного пользователя закрыт'
    elif code == 113:
        return 'Неверный идентификатор пользователя'
    elif code == 200:
        return 'Доступ к альбому запрещен'
    else:
        return ''


def check_folders(token_yan: str, id_vk: str):
    headers = {'Authorization': f'OAuth {token_yan}'}
    params = {'path': f'Резервные фотографии с ВК/{id_vk}'}
    url_yan = 'https://cloud-api.yandex.net/v1/disk/resources'
    response = requests.get(url_yan, headers=headers, params=params)
    return True if response.status_code == 200 else False


def create_main_folder(token_yan: str):
    headers = {'Authorization': f'OAuth {token_yan}'}
    params = {'path': 'Резервные фотографии с ВК'}
    url_yan = 'https://cloud-api.yandex.net/v1/disk/resources'
    response = requests.get(url_yan, headers=headers, params=params)
    if response.status_code != 200:
        requests.put(url_yan, headers=headers, params=params)


def clear_folder(token_yan, profile, album):
    path = f'Резервные фотографии с ВК/{profile}/{album}'
    headers = {'Authorization': f'OAuth {token_yan}'}
    params = {'path': path}
    url_yan = 'https://cloud-api.yandex.net/v1/disk/resources'
    requests.delete(url_yan, headers=headers, params=params)
    shutil.rmtree(path)
    os.remove(f'photos_info/{profile}/{album}.json')


print('Введите ID страницы VK, с которой хотите сохранить фотографии, и ваш токен с полигона Яндекс.Диска')
vk_id = str(input('ID страницы VK: '))
token = str(input('Токен: '))
create_main_folder(token)
profiles[vk_id] = VKAPI(vk_id, token)
if check_folders(token, vk_id):
    profiles[vk_id].get_created_folders()
while trigger == True:
    status_check = profiles[vk_id].get_albums()
    if (list(status_check.keys())[0]) == 'error':
        msg_error = error_msg_vk(status_check['error']['error_code'])
        print(f'Ошибка!\n{msg_error}')
    elif status_check['response']['count'] == 0:
        print('В выбранном профиле нет доступных альбомов')
    else:
        albums = status_check['response']
        print(print_albums_input(albums))
        album_id = int(input('Введите номер выбранного альбома: '))
        sel_album = albums['items'][album_id - 1]
        album_name = profiles[vk_id].get_albums_names(sel_album)
        if album_name in profiles[vk_id].downloaded_albums:
            count_dwnld_photos = profiles[vk_id].check_folders(album_name).json()['_embedded']['total']
            print(f'Найдены уже скаченные фотографии из данного альбома '
                  f'в количестве {count_dwnld_photos} шт.\n'
                  f'Выберите действие:\n'
                  f'1 - Перезаписать существующие фотографии\n'
                  f'2 - Продолжить скачивание фотографий, начиная с последней')
            action = int(input('Ваше действие: '))
            if action == 1:
                clear_folder(token, vk_id, album_name)
                count = 0
            elif action == 2:
                count = count_dwnld_photos
        photos_count = int(input('Введите количество фотографий для скачивания '
                                 '(счет начинается с более старых): '))
        print('=' * 40)
        profiles[vk_id].reserve_photo(photos_count, sel_album, count)
    print('Выберите действие:\n'
          '1 - Выбрать другой альбом\n'
          '2 - Выбрать другого пользователя VK\n'
          '3 - Выход')
    choice = int(input('Ваш выбор: '))
    print('=' * 40)
    if choice == 3:
        break
    elif choice == 1:
        continue
    elif choice == 2:
        vk_id = str(input('ID страницы VK: '))
        if vk_id not in profiles.keys():
            profiles[vk_id] = VKAPI(vk_id, token)
            if check_folders(token, vk_id):
                profiles[vk_id].get_created_folders()
