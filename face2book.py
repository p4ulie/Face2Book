#!/usr/bin/env python

'''Main description

Additional description
'''

# imports

__author__ = "Pavol Antalík"
__copyright__ = "Copyright 2018, Pavol Antalík"
__credits__ = ["Pavol Antalík"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Pavol Antalík"
__email__ = "pavol.antalik@gmail.com"
__status__ = "Prototype"

import simplejson as json
import pytz
from datetime import datetime, timezone, tzinfo

import re
from functools import partial

from jinja2 import Template

# from IPython.display import Image

local_timezone = pytz.timezone('Europe/Bratislava')

file_name = "posts/your_posts.json"

fix_mojibake_escapes = partial(
     re.compile(rb'\\u00([\da-f]{2})').sub,
     lambda m: bytes.fromhex(m.group(1).decode()))

with open(file_name, 'rb') as binary_data:
    repaired = fix_mojibake_escapes(binary_data.read())
posts = json.loads(repaired.decode('utf8'))

status_updates = posts['status_updates']

# status_updates_sorted_timestamp_asc = sorted(status_updates, key=lambda k: k['timestamp'], reverse=False)

import operator

from argparse import ArgumentParser

def main(year="2008"):
    """
    Main function for testing the classes
    """
    status_updates_sorted_timestamp_asc = status_updates.sort(key=operator.itemgetter('timestamp'))

    c = 0
    date_str_year = '0000'
    date_str_year_month = '0000'
    date_str_year_month_day = '0000'

    print('<html>')
    print('<head>')
    print('<title>Offline Facebook Diary</title>')
    print('</head>')
    print('<body>')

    print()
    for status_update in status_updates:
        c = c + 1
    #    if c == 100:
    #        break


        timestamp = status_update['timestamp']

        title = None
        if 'title' in status_update.keys():
            title = status_update['title']

        if ((title is None) or \
            ((title[-14:] != 'shared a link.') and \
             (title[-14:] != 'shared a post.') and \
             (title[-15:] != 'shared a photo.') and \
             (title[-15:] != 'shared a video.'))) \
                and (datetime.fromtimestamp(timestamp, local_timezone).strftime('%Y') == year):

            attachments = None
            if 'attachments' in status_update.keys():
                attachments = status_update['attachments']  # list of dicts, dicts contain "data" keys, contain lists

            if datetime.fromtimestamp(timestamp, local_timezone).strftime('%Y') != date_str_year:
                date_str_year = datetime.fromtimestamp(timestamp, local_timezone).strftime('%Y')
                print('<h1>',date_str_year, '</h1>')

            if datetime.fromtimestamp(timestamp, local_timezone).strftime('%B %Y') != date_str_year_month:
                date_str_year_month = datetime.fromtimestamp(timestamp, local_timezone).strftime('%B %Y')
                print('<h2>',date_str_year_month, '</h2>')

            if datetime.fromtimestamp(timestamp, local_timezone).strftime('%d.%m.%Y') != date_str_year_month_day:
                date_str_year_month_day = datetime.fromtimestamp(timestamp, local_timezone).strftime('%d.%m.%Y')
                print('<h3>',date_str_year_month_day, '</h3>')

            date_str = datetime.fromtimestamp(timestamp, local_timezone).strftime('%H:%M')
            print('<p><i>', date_str, ':</i> ', sep='', end='')

            if title is not None:
                print('<i>', title, '</i></p>', sep='', end='\n\n')

            data_list = None
            if 'data' in status_update.keys():
                data_list = status_update['data']  # list of dicts, dicts contain "post" keys

                for data in data_list:
                    data_post = None
                    if 'post' in data.keys():
                        data_post = data['post']
                    print('\n<p>\n', data_post, '\n</p>\n', sep='', end='\n\n')

            if attachments is not None:
                for attachment in attachments:
                    attachment_data_list = attachment['data']
                    for attachment_data in attachment_data_list:
                        attachment_data_media = None
                        attachment_data_note = None
                        if 'media' in attachment_data.keys():
                            attachment_data_media = attachment_data['media']
                            attachment_data_media_uri = attachment_data_media['uri']
                            print('<p><img src="', attachment_data_media_uri,'" width=75%></p>',sep='', end='\n')

                            if 'comments' in attachment_data_media:
                                print('<p>', 'Comments: ', '</p>', sep='', end='\n')
                                for attachment_data_media_comment in attachment_data_media['comments']:
                                    comment_author = attachment_data_media_comment['author']
                                    comment_comment = attachment_data_media_comment['comment']
                                    print('<p>', comment_author, ': ', comment_comment, '</p>', sep='', end='\n')

                        if 'note' in attachment_data.keys():
                            attachment_data_note = attachment_data['note']
                            print('<p>', attachment_data_note['title'],'</p>', sep='')
                            print('<p>: ', attachment_data_note['text'],'</p>', sep='')


                        # print('attachment types: ', attachment_data.keys())

            print('<hr>')

    print('</body>')
    print('</html>')

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-y', help='Year')

    args = parser.parse_args()

    if args.y is not None:
        year = args.y

    main(year)