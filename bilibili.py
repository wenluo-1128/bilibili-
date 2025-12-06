from DrissionPage import ChromiumPage
import requests
import re
import json
from bs4 import BeautifulSoup
import pandas as pd



def video_info(bvid):
    video_data = {
        'bvid': bvid,
        'title': None,
        'publish_time': None,
        'duration': None,
        'likes': None,
        'favorites': None,
        'comments': None
    }
    headers = {
    'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0'
    }
    url = f'https://www.bilibili.com/video/{bvid}/?spm_id_from=333.788'
    resp = requests.get(url, headers=headers)

    soup = BeautifulSoup(resp.text, 'html.parser')

    title_element = soup.find('h1', {'class': 'video-info-title-inner'}) or soup.find('h1')
    title_time = soup.find('div', {'class': 'pubdate-ip-text'})
    script_content = soup.find('script', string=re.compile('window.__INITIAL_STATE__'))

    if title_element:
        video_data['title'] = title_element.get_text(strip=True)
    if title_time:
        video_data['publish_time'] = title_time.get_text(strip=True)


    if script_content and script_content.string:
        try:
            json_str = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', script_content.string, re.DOTALL)
            if json_str:
                initial_state = json.loads(json_str.group(1))
                channel_kv = initial_state.get('channelKv', [])
                videoData = initial_state.get('videoData', {})
                stat = videoData.get('stat', {})
                reply = stat.get('reply')
                like = stat.get('like')
                favorite = stat.get('favorite')
                video_data['favorites'] = favorite
                video_data['likes'] = like
                video_data['comments'] = reply
            else:
                print(f'未找到__INITIAL_STATE__数据 for bvid: {bvid}')
        except Exception as e:
            print(f'解析JSON出错 for bvid: {bvid}: {e}')
    else:
        print(f'未找到包含__INITIAL_STATE__的script标签 for bvid: {bvid}')
    return video_data

if __name__ == '__main__':
    up = input('请输入up主的uid: ')
    indexs = int(input('请输入要爬取的页数: '))
    url_up = f'https://space.bilibili.com/{up}/upload/video'
    all_videos_data = []

    chrom = ChromiumPage()
    chrom.listen.start('api.bilibili.com/x/space/wbi/arc/search')
    chrom.get(url_up)
    for page in range(indexs): 
        print(f'正在处理第 {page + 1} 页...')
        resp = chrom.listen.wait()
        Jsondata = resp.response.body
        if Jsondata and 'data' in Jsondata and 'list' in Jsondata['data'] and 'vlist' in Jsondata['data']['list']:
            for item in Jsondata['data']['list']['vlist']:
                bvid = item['bvid']
                duration_str = item['length']

                current_video_data = video_info(bvid)
                if current_video_data:
                    current_video_data['duration'] = duration_str # Add duration from the list API
                    all_videos_data.append(current_video_data)
                    print(f"已收集: {current_video_data['title']}")
                else:
                    print(f"未能获取 {bvid} 的详细信息")
        else:
            print("未能从响应中获取视频列表数据")
            break

        try:
            next_page_buttons = chrom.eles('.vui_button vui_pagenation--btn vui_pagenation--btn-side')
            if len(next_page_buttons) > 1:
                next_page_buttons[1].click() # 点击第二个按钮
            elif len(next_page_buttons) == 1:
                next_page_buttons[0].click() # 点击第一个按钮
            else:
                print("未找到下一页按钮")
                break
        except Exception as e:
            print(f"点击下一页时出错或未找到下一页按钮: {e}")
            break

    chrom.quit()

    if all_videos_data:
        df = pd.DataFrame(all_videos_data)
        df.rename(columns={
            'bvid': 'bv号',
            'title': '标题',
            'publish_time': '视频发布时间',
            'duration': '视频时长',
            'likes': '点赞数量',
            'favorites': '收藏数量',
            'comments': '评论数量'
        }, inplace=True)
        excel_path = f'\\play_python\\爬虫\\B站uid为{up}的视频数据.xlsx'
        df.to_excel(excel_path, index=False)
        print(f'数据已保存到 {excel_path}')
    else:
        print('没有收集到任何视频数据。')
