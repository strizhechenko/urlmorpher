# coding:utf-8

__author__ = 'Oleg Strizhechenko <oleg@carbonsoft.ru>'

import re
import urllib
import urlparse
import sys

not_idna_host = re.compile('^[a-zA-Z:\.0-9-]+$')


def idna(url_set_in):
    out = url_set_in.copy()
    for url in url_set_in:
        host = pick_host(url)
        if not_idna_host.match(host):
            continue
        out.add(url.replace(host, host.encode('idna'), 1))
        out.remove(url)
    return out


def lower(url_set_in):
    out = url_set_in.copy()
    for url in filter(lambda url: not url.islower(), url_set_in):
        host = pick_host(url)
        out.add(re.sub("(?i)" + host, host.lower(), url))
    return out


def www(url_set_in):
    out = url_set_in.copy()
    for url in filter(lambda u: u[7:11] == u'www.', url_set_in):
        out.add(url.replace(u'www.', u'', 1))
        if pick_host(url).count(u'.') < 3:
            out.remove(url)
    return out


def fqdn(url_set_in):
    out = url_set_in.copy()
    for url in url_set_in:
        host = pick_host(url)
        if host.endswith('.'):  # is fqdn host
            out.add(url.replace(host, host.rstrip('.')))
        else:  # is norm host
            out.add(url.replace(host, host + '.'))
    return out


def cp1251(url_set_in):
    out = url_set_in.copy()
    for url in url_set_in:
        out.add(url.encode('cp1251'))
    return out


def domain_change(url_set_in):
    replaces = {
        "vk.com": "vkontakte.ru",
        "vkontakte.ru": "vk.com"
    }
    out = url_set_in.copy()
    for url in url_set_in:
        host = pick_host(url)
        if host in replaces:
            out.add(url.replace(host, replaces.get(host)))
    return out


def get_quote(get, safe="/"):
    if type(get) == unicode:
        return urllib.quote(get.encode('utf-8'), safe).decode('utf-8')
    return urllib.quote(get).decode('utf-8')


def mixed_quote_fix(url, host, get):
    escaped = re.compile('%[0-9A-F]{2}')
    safe_mixed = escaped.findall(get)
    if not safe_mixed:
        return None
    safe = "#&(),*+:/;=?@~%"
    for char in set(escaped.findall(get)):
        safe = safe.replace(urllib.unquote(char), '')
    if type(get) == unicode:
        get = get.encode('utf-8')
    if type(safe) == unicode:
        safe = safe.encode('utf-8')
    # print  type(get), type(safe)
    new_get = urllib.quote(get, safe)
    return 'http://' + host + new_get


def url_quote_unquote(url_set_in):
    out = url_set_in.copy()
    for url in url_set_in:
        host = pick_host(url)
        get = pick_get(url)
        quote_full = 'http://' + host + get_quote(get)
        if type(url) == type(quote_full) and url == quote_full:
            continue
        out.add(quote_full)
        out.add('http://' + host + get_quote(get, "#&(),*+:/;=?@~"))
        if url.find('%') >= 0:
            unquote_url = 'http://' + host + urllib.unquote(get)
            if type(url) == unicode and url == unquote_url:
                continue
            out.add(unquote_url)
            mixed = mixed_quote_fix(url, host, get)
            if mixed:
                out.add(mixed)
    return out


def reduce_length(url_set_in):
    out = url_set_in.copy()
    for url in url_set_in:
        if len(url) > 600:
            out.add(__reduce_length(url))
            out.remove(url)
    return out


def __reduce_length(url):
    if len(url) > 600:
        return __reduce_length(__strip_to_slash(url))
    return url


def __strip_to_slash(url, symbol='/'):
    return url[:url.rfind(symbol)]


def sharp_remove(url_set_in):
    out = url_set_in.copy()
    for url in url_set_in:
        if pick_get(url).find('#') >= 0:
            out.add(url[:url.rfind('#')])
            out.add(url[:url.find('#')])
    return out


def valid_http_only(url_set_in):
    return set(filter(
        lambda u: u.startswith(u'http://') and u.find('.') > 0, url_set_in
    ))


def is_only_url(url):
    get = pick_get(url)
    return not get or get == '/'


def domain_only_urls(url_set_in):
    return set(map(lambda u: u.rstrip('/'), filter(is_only_url, url_set_in)))


def fulldomain_reduce(url_set_in):
    out = url_set_in.copy()
    domain_only = map(pick_host, domain_only_urls(url_set_in))
    for url in url_set_in:
        host = pick_host(url)
        if host in domain_only and url != 'http://' + host:
            out.remove(url)
            out.add('http://' + host)
    return out


def remove_bad_symbols_parts(url_set_in):
    out = url_set_in.copy()
    for url in filter(lambda u: type(u) == unicode, url_set_in):
        if url.find(u'Р') >= 0:
            out.add(remove_bad_symbol_all(url, u'Р'))
            out.remove(url)
    return out


def remove_bad_symbol_all(url, symbol):
    """ Оставляем не больше 3 частей GET чтобы блочить через complete """
    if url.find(symbol) >= 0 or url.count('/', 7) > 3:
        stripped_url = __strip_to_slash(url)
        return remove_bad_symbol_all(stripped_url, symbol)
    return url


def slash(url_set_in):
    out = url_set_in.copy()
    for url in url_set_in:
        if url.endswith('/') and url.count('/') < 6:
            out.add(url.rstrip('/'))
            out.remove(url)
            continue
        if not url.endswith('/') and url.count('/') > 6:
            out.add(url + '/')
        if url.find('?') >= 0:
            out.add(url.replace('?', '/?', 1))
            if url.find('/?') >= 0:
                out.add(url.replace('/?', '?', 1))
    for url in out.copy():
        if url.find('//', 7) > 0:
            out.remove(url)
            out.add("%s%s" % (u'http://', url[7:].replace('//', '/')))
    return out


def pick_host(url):
    return urlparse.urlsplit(url)[1]


def pick_get(url):
    return url[len(pick_host(url)) + 7:]


functions_ordered = (
    valid_http_only,
    lower,
    domain_change,
    # fulldomain_reduce,
    www,
    fqdn,
    idna,
    slash,
    sharp_remove,
    cp1251,
    reduce_length,
    url_quote_unquote,
    remove_bad_symbols_parts
)
