# SPDX-FileCopyrightText: 2024 PeARS Project, <community@pearsproject.org> 
#
# SPDX-License-Identifier: AGPL-3.0-only

from os.path import dirname, realpath, join, isfile
from pathlib import Path
import joblib
import numpy as np
from scipy.sparse import csr_matrix, load_npz, vstack, save_npz
from app import db, models, VEC_SIZE
from app.api.models import Urls, Pods
from app.indexer.posix import load_posix, dump_posix

dir_path = dirname(dirname(realpath(__file__)))
pod_dir = join(dir_path,'app','static','pods')

def parse_pod_name(pod_name):
    print(pod_name)
    theme = pod_name.split('.u.')[0]
    contributor = pod_name.split('.u.')[1]
    lang = Pods.query.filter_by(name=pod_name).first().language
    return contributor, theme, lang


###########
# Creating
###########

def create_idx_to_url(contributor):
    """ Doc ID to URL table initialisation.
    This happens once when the user indexes
    for the first time.
    """
    # One idx to url dictionary per user
    user_dir = join(pod_dir,contributor)
    Path(user_dir).mkdir(parents=True, exist_ok=True)
    user_path = join(user_dir, contributor+'.idx')
    if not isfile(user_path):
        print("Making idx dictionaries for new user.")
        idx_to_url = [[],[]]
        joblib.dump(idx_to_url, user_path)


def create_pod_npz_pos(contributor, theme, lang):
    """ Pod npz and pos initialisation.
    This happens when the user indexes for the 
    first time under a specific theme.
    """
    user_dir = join(pod_dir,contributor, lang)
    Path(user_dir).mkdir(parents=True, exist_ok=True)
    pod_path = join(user_dir, theme+'.u.'+contributor )
    vocab = models[lang]['vocab']
    if not isfile(pod_path+'.npz'):
        print("Making 0 CSR matrix for new pod")
        pod = np.zeros((1,VEC_SIZE))
        pod = csr_matrix(pod)
        save_npz(pod_path+'.npz', pod)
        print("create_pod_npz_pos", pod.shape[0])

    if not isfile(pod_path+'.pos'):
        print("Making empty positional index for new pod")
        posindex = [{} for _ in range(len(vocab))]
        joblib.dump(posindex, pod_path+'.pos')

    if not isfile(pod_path+'.npz.idx'):
        print("Making idx dictionaries for new pod")
        # Lists of lists to make deletions easier
        npz_to_idx = [[0],[-1]] # For row 0 of the matrix
        joblib.dump(npz_to_idx, pod_path+'.npz.idx')


def create_pod_in_db(contributor, theme, lang):
    '''If the pod does not exist, create it in the database.
    '''
    if contributor is not None:
        theme = theme+'.u.'+contributor
    url = join("http://localhost:8080/api/pods/",contributor,lang,theme.replace(' ', '+'))
    if not db.session.query(Pods).filter_by(url=url).all():
        p = Pods(url=url)
        p.name = theme
        p.description = theme
        p.language = lang
        p.registered = True
        db.session.add(p)
        db.session.commit()

def create_or_replace_url_in_db(url, title, snippet, theme, lang, note, share, contributor, entry_type):
    """Add a new URL to the database or update it.
    Arguments: url, title, snippet, theme, language,
    note warning, username, type (url or doc).
    """
    cc = False
    entry = db.session.query(Urls).filter_by(url=url).first()
    if entry:
        u = db.session.query(Urls).filter_by(url=url).first()
    else:
        u = Urls(url=url)
    u.title = title
    u.snippet = snippet
    u.pod = theme+'.u.'+contributor
    u.language = lang
    u.share = share
    u.contributor = contributor
    u.doctype = entry_type
    u.cc = cc
    if note != '':
        note = '@'+contributor+' >> '+note
        if u.notes is not None:
            u.notes = u.notes+'<br>'+note
        else:
            u.notes = note
    db.session.add(u)
    db.session.commit()

###########
# Loading
###########

def load_idx_to_url(contributor):
    user_dir = join(pod_dir,contributor)
    path = join(user_dir, contributor+'.idx')
    idx_to_url = joblib.load(path)
    return idx_to_url, path

def load_npz_to_idx(contributor, lang, theme):
    user_dir = join(pod_dir, contributor, lang)
    pod_path = join(user_dir, theme+'.u.'+contributor+'.npz.idx')
    npz_to_idx = joblib.load(pod_path)
    return npz_to_idx, pod_path


##########
# Adding
##########

def add_to_npz(v, pod_path):
    """ Add new pre-computed vector to npz matrix.
    Arguments:
    v: the vector to add
    pod_path: the path to the target pod

    Returns:
    vid: the new row number for the vector
    """
    pod_m = load_npz(pod_path)
    pod_m = vstack((pod_m,csr_matrix(v)))
    save_npz(pod_path, pod_m)
    vid = pod_m.shape[0]
    return vid


def add_to_idx_to_url(contributor, url):
    """Add an entry to the IDX to URL map.
    Arguments: username, url.
    Return: the newly create IDX for this url.
    """
    idx_to_url, pod_path = load_idx_to_url(contributor)
    if len(idx_to_url[0]) > 0:
        idx = idx_to_url[0][-1]+1
    else:
        idx = 0
    idx_to_url[0].append(idx)
    idx_to_url[1].append(url)
    joblib.dump(idx_to_url, pod_path)
    return idx


def add_to_npz_to_idx(pod_name, lang, vid, idx):
    """Record the ID of the document given
    its position in the npz matrix.
    NB: the lists do not have to be in the
    order of the matrix.
    """
    contributor = pod_name.split('.u.')[1]
    user_dir = join(pod_dir,contributor)
    pod_path = join(user_dir, lang, pod_name+'.npz.idx')
    npz_to_idx = joblib.load(pod_path)
    npz_to_idx[0] = list(range(vid))
    npz_to_idx[1].append(idx)
    joblib.dump(npz_to_idx, pod_path)


############
# Deleting
############

def delete_url_representations(url):
    """ Delete url with some url on some pod.
    """
    u = db.session.query(Urls).filter_by(url=url).first()
    pod = u.pod
    username = pod.split('.u.')[1]
    print("POD",pod,"USER",username)
    idx = rm_from_idx_to_url(username, url)
    vid = rm_from_npz_to_idx(pod, idx)

    #Remove document row from .npz matrix
    rm_from_npz(vid, pod)

    #Remove doc from positional index
    rm_doc_from_pos(idx, pod)

    #Delete from database
    db.session.delete(u)
    db.session.commit()
    return "Deleted document with url "+url


def rm_from_idx_to_url(contributor, url):
    idx_to_url, path = load_idx_to_url(contributor)
    print("IDX_TO_URL BEFORE RM",idx_to_url)
    i = idx_to_url[1].index(url)
    idx = idx_to_url[0][i]
    idx_to_url[0].pop(i)
    idx_to_url[1].pop(i)
    print("IDX_TO_URL AFTER RM",idx_to_url)
    print("INDEX OF REMOVED ITEM",idx)
    joblib.dump(idx_to_url, path)
    return idx

def rm_from_npz_to_idx(pod_name, idx):
    """Remove doc from npz to idx record.
    NB: the lists do not have to be in the
    order of the matrix.
    """
    contributor, theme, lang = parse_pod_name(pod_name)
    npz_to_idx, pod_path = load_npz_to_idx(contributor, lang, theme)
    print("NPZ_TO_IDX BEFORE RM:",npz_to_idx)
    i = npz_to_idx[1].index(idx)
    npz_to_idx[1].pop(i)
    npz_to_idx[0] = list(range(len(npz_to_idx[1])))
    print("NPZ_TO_IDX AFTER RM:",npz_to_idx)
    print("INDEX OF REMOVED ITEM",i)
    joblib.dump(npz_to_idx, pod_path)
    return i


def rm_from_npz(vid, pod_name):
    """ Remove vector from npz file.
    Arguments:
    vid: the row number of the vector
    pod_path: the path to the pod containing the vector

    Returns: the deleted vector
    """
    contributor, _, lang = parse_pod_name(pod_name)
    pod_path = join(pod_dir, contributor, lang, pod_name+'.npz')
    pod_m = load_npz(pod_path)
    print("SHAPE OF NPZ MATRIX BEFORE RM:",pod_m.shape)
    v = pod_m[vid]
    print("CHECKING SHAPE OF DELETED VEC:",pod_m.shape)
    m1 = pod_m[:vid]
    m2 = pod_m[vid+1:]
    pod_m = vstack((m1,m2))
    print("SHAPE OF NPZ MATRIX AFTER RM:",pod_m.shape)
    save_npz(pod_path, pod_m)
    return v


def rm_doc_from_pos(vid, pod):
    """ Remove wordpieces from pos file.
    Arguments:
    vid: the ID of the vector recording the wordpieces
    pod: the name of the pod

    Returns: the content of the positional index for that vector.
    """
    contributor, theme, lang = parse_pod_name(pod)
    vocab = models[lang]['vocab']
    posindex = load_posix(contributor, lang, theme)
    remaining_posindex = []
    deleted_posindex = []
    print("DELETING DOC ID",vid)
    for token in vocab:
        token_id = vocab[token]
        tmp_remaining = {}
        tmp_deleted = {}
        for doc_id, posidx in posindex[token_id].items():
            if doc_id != vid:
                tmp_remaining[doc_id] = posidx
            else:
                tmp_deleted[doc_id] = posidx
        remaining_posindex.append(tmp_remaining)
        deleted_posindex.append(tmp_deleted)
    dump_posix(remaining_posindex, contributor, lang, theme)
    return deleted_posindex

