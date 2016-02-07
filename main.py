#! /usr/bin/env python

"""
Main controller.
"""

__author__ = 'Madison'

import feedparser
import sqlite3 as db
from envelopes import Envelope
import requests
from bs4 import BeautifulSoup
import re


def get_craiglist_current(source_url):
    """
    using our search params, go get current CL content
    :return:
    """
    result = feedparser.parse(source_url)
    links = [str(item['dc_source']) for item in result["items"]]

    return links


def compare_vs_db(current_links):
    """
    compare current CL results against db.  If there are new items, add them and prepare to mail them
    :return:
    """

    new_posts = []

    con = db.connect('db.sqlite3')

    with con:
        cur = con.cursor()

        for each_link in current_links:
            cur.execute('select post from data where post = ?;', (each_link,))
            data = cur.fetchone()

            if data is None:
                new_posts.append(each_link)
                cur.execute('insert INTO data (post) values (?);', (each_link,))

    return new_posts


def pull_html_from_post(post_url):
    html_content = ''

    try:
        resp = requests.get(post_url, timeout=5)
        resp.raise_for_status()  # <- no-op if status!=200
    except Exception, e:
        print 'problem getting email.....'
        return '(error getting content: {})'.format(e)

    # should have a response obj here
    parsed_page = BeautifulSoup(resp.content, "html.parser", from_encoding=resp.encoding)

    title = parsed_page.find('title').text.encode('utf-8')
    full_text = parsed_page.find("section", {"id": "postingbody"}).text
    image_div = parsed_page.find("div", {"id": re.compile('1_image.*')})  # id is always 1_image*

    image = image_div.find("img")

    html_content += '<b>' + str(title) + '</b> <br>'

    try:
        print image
        full_text += '<img src="' + image['src'] + '">'
    except KeyError, k:
        html_content += 'error getting image... {}'.format(k)

    html_content += '<p>' + str(full_text) + '</p>'

    return html_content


def mail_new_entries(links):
    """
    given a list of new entries, mail out to subscriber list
    :return:
    """

    recipients = ['hot6lpyxis@gmail.com']

    html_start = ''

    for each_link in links:
        html_start += '<p>'
        html_start += str(each_link)
        html_start += '<br>'
        html_start += '<hr>'

        html_start += pull_html_from_post(each_link)

        html_start += '</p>'

    html_start += '</body></html>'

    print html_start

    envp = Envelope(from_addr='donotreply@jakemadison.com', to_addr=recipients,
                    subject='New CL posting!', html_body=html_start)

    envp.send('localhost')




def main():

    search_url = ('http://vancouver.craigslist.ca/search/van/apa?format=rss'
                  '&hasPic=1&is_paid=all&max_price=1500&pets_cat=1')
    print 'getting new content'
    cl_content = get_craiglist_current(search_url)
    
    print 'comparing to db'
    new_posts = compare_vs_db(cl_content)

    if new_posts:
        print 'mailing new entries {}'.format(new_posts)
        mail_new_entries(new_posts)
    else:
        mail_new_entries(['http://vancouver.craigslist.ca/van/apa/5436583951.html'])
        print 'no new entries'


if __name__ == '__main__':
    main()



