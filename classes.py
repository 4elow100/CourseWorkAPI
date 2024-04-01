import requests
import os
import json
from datetime import datetime


class DictOfPhotos:
    def __init__(self, data: dict):
        self.data = data

    @staticmethod
    def _url_of_photo_with_max_size(photo_json: dict) -> list:
        pixels = 0
        url = ''
        size = ''
        for photo in photo_json['sizes']:
            if photo['width'] * photo['height'] > pixels:
                pixels = photo['width'] * photo['height']
                url = photo['url']
                size = photo['type']
        return [url, size]

    def _get_names(self, likes: str,date :str, all_names: list):
        curr_name = f'{likes}.jpg'
        i = False
        for name in all_names[::-1]:
            if likes == name.split('_')[0]:
                i = True
                if len(name.split('_')) > 1:
                    if date == name.split('_')[1]:
                        if len(name.split('_')) > 2:
                            curr_name = f'{likes}_{date}_{int(name.split('_')[-1]) + 1}.jpg'
                            i = False
                            break
                        else:
                            curr_name = f'{likes}_{date}_2.jpg'
                            i = False
                            break
        if i:
            curr_name = f'{likes}_{date}.jpg'
        return curr_name

    def sorted_photos(self, count: int, count_dwnld: int, all_name: list) -> dict:
        photos_dict = {}
        photos_list = []
        all_names = all_name
        for photo in self.data['items']:
            url_size_list = self._url_of_photo_with_max_size(photo)
            photo_item = {}
            photo_item['name'] = self._get_names(
                str(photo['likes']['count']), str(datetime.fromtimestamp(photo['date']).date()), all_names)
            photo_item['id'] = photo['id']
            photo_item['link'] = url_size_list[0]
            photo_item['date'] = photo['date']
            photo_item['likes'] = photo['likes']['count']
            photo_item['size'] = url_size_list[1]
            all_names.append(photo_item['name'][:-4])
            photos_list.append(photo_item)
        for photo in photos_list[count_dwnld:count+count_dwnld]:
            photos_dict[photo['name']] = photo
        return photos_dict


class VKAPI:

    def __init__(self, id_vk, token):
        self.id_vk = id_vk
        self.token = token
        self.downloaded_albums = []

    def _common_params(self):
        service_token = '889079f9889079f9889079f9a08b87dfee88890889079f9ed69b06600a50bfa79cb3cbf'
        return {
            'access_token': service_token,
            'v': '5.199',
            'owner_id': self.id_vk,
        }

    def _common_headers(self):
        return {'Authorization': f'OAuth {self.token}'}

    @staticmethod
    def _gen_link(method) -> str:
        url = 'https://api.vk.com/method/'
        return f'{url+method}'

    def get_albums(self):
        params = self._common_params()
        params.update({
            'need_system': 1
        })
        return requests.get(self._gen_link('photos.getAlbums'), params=params).json()

    def get_created_folders(self):
        response = self.check_folders('').json()
        for folder in response['_embedded']['items']:
            if folder['type'] == 'dir':
                self.downloaded_albums.append(folder['name'])

    @staticmethod
    def get_albums_names(album: dict) -> str:
        if album['id'] == -6:
            album_name = 'Фотографии профиля'
        elif album['id'] == -7:
            album_name = 'Фотографии со стены'
        else:
            album_name = f'{album["title"]}'
        return album_name

    def get_photos(self, album: str) -> dict:
        params = self._common_params()
        params.update({
            'album_id': album,
            'extended': 1,
        })
        return requests.get(self._gen_link('photos.get'), params=params).json()['response']

    def check_folders(self, album: str):
        headers = self._common_headers()
        params = {'path': f'Резервные фотографии с ВК/{self.id_vk}/{album}'}
        return requests.get('https://cloud-api.yandex.net/v1/disk/resources',
                            headers=headers, params=params)

    def _get_dwn_photos_names(self, album_name: str) -> list:
        all_names = []
        photos_list = self.check_folders(album_name).json()['_embedded']['items']
        for photo in photos_list:
            all_names.append(photo['name'])
        return all_names

    def _create_json(self, album_name: str, photos: dict):
        files = []
        json_name = f'photos_info/{self.id_vk}/{album_name}.json'
        if os.path.exists(json_name):
            with open(json_name, 'r') as f:
                file_content = f.read()
                if file_content:
                    files = json.loads(file_content)
                else:
                    pass
        for photo in photos.values():
            files.append({'file_name': photo['name'], 'size': photo['size']})
        with open(json_name, 'w') as f:
            json.dump(files, f, indent=4)
        print(f'Информация о фотографиях успешно сохранена в файле "{album_name}.json"')

    def download_photo(self, count: int, album_id: str, album_name: str, count_dwnld: int) -> dict:
        photos = self.get_photos(album_id)
        all_names = []
        if count_dwnld > 0:
            all_names = self._get_dwn_photos_names(album_name)
        album_dict = {album_id: DictOfPhotos(photos)}
        photos_dict = album_dict[album_id].sorted_photos(count, count_dwnld, all_names)
        i = 0
        if photos['count'] - count_dwnld < count:
            print('Фотографий в выбранном альбоме меньше, чем было указано в запросе на загрузку!\n'
                  'Будут загружены все фотографии из выбранного альбома.')
        for photo in photos_dict:
            i += 1
            print(f'Идет скачивание фотографий из выбранного альбома и '
                  f'профиля VK ({i}/{len(photos_dict)})')
            response = requests.get(photos_dict[photo]['link'])
            with open(f'Резервные фотографии с ВК/{self.id_vk}/{album_name}/{photo}', 'wb') as f:
                f.write(response.content)
        print('Скачивание завершено')
        return photos_dict

    def upload_photos(self, count: int, album: dict, count_dwnld: int):
        headers = self._common_headers()
        album_name = self.get_albums_names(album)
        photos_dict = self.download_photo(count, album['id'], album_name, count_dwnld)
        self._create_json(album_name, photos_dict)
        i = 0
        for photo in photos_dict:
            i += 1
            print(f'Идет загрузка фотографий на Яндекс.Диск ({i}/{len(photos_dict)})')
            response_link_upload = requests.get(f'https://cloud-api.yandex.net/v1/disk/resources/upload',
                                                headers=headers,
                                                params={'path': f'Резервные фотографии с ВК'
                                                                f'/{self.id_vk}/{album_name}/{photo}'})
            url_for_upload = response_link_upload.json()['href']
            with open(f'Резервные фотографии с ВК/{self.id_vk}/{album_name}/{photo}', 'rb') as f:
                requests.put(url_for_upload, files={'file': f})
        print('Загрузка завершена\n', '=' * 40)

    def reserve_photo(self, count: int, album: dict, count_dwnld: int):
        headers = self._common_headers()
        url_yan = 'https://cloud-api.yandex.net/v1/disk/resources'
        main_folder_name = 'Резервные фотографии с ВК'
        album_name = self.get_albums_names(album)
        if not os.path.exists(f'{main_folder_name}/{self.id_vk}'):
            os.mkdir(f'{main_folder_name}/{self.id_vk}')
            if self.check_folders("").status_code != 200:
                requests.put(url_yan, headers=headers,
                             params={'path': f'{main_folder_name}/{self.id_vk}'})
        if not os.path.exists(f'photos_info/{self.id_vk}'):
            os.mkdir(f'photos_info/{self.id_vk}')
        if not os.path.exists(f'{main_folder_name}/{self.id_vk}/{album_name}'):
            os.mkdir(f'{main_folder_name}/{self.id_vk}/{album_name}')
            if self.check_folders(album_name).status_code != 200:
                requests.put(url_yan, headers=headers,
                             params={'path': f'{main_folder_name}/{self.id_vk}/{album_name}'})
            self.upload_photos(count, album, count_dwnld)
            self.downloaded_albums.append(album_name)
        else:
            self.upload_photos(count, album, count_dwnld)
