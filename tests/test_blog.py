import pytest
from flaskr.db import get_db


def test_index(client, auth):
    response = client.get('/')
    assert b"Log In" in response.data
    assert b"Register" in response.data

    auth.login()
    response = client.get('/')
    assert b'Log Out' in response.data
    assert b'test title' in response.data
    assert b'by test on 2018-01-01' in response.data
    assert b'test\nbody' in response.data
    assert b'href="/post/1/update"' in response.data
    assert b'href="/post/1"' in client.get('/').data


@pytest.mark.parametrize('path', (
    '/post/create',
    '/post/1/update',
    '/post/1/delete',
))
def test_login_required(client, path):
    response = client.post(path)
    assert response.headers["Location"] == "/auth/login"


def test_author_required(app, client, auth):
    # change the post author to another user
    with app.app_context():
        db = get_db()
        db.execute('UPDATE post SET author_id = 2 WHERE id = 1')
        db.commit()

    auth.login()
    # current user can't modify other user's post
    assert client.post('/post/1/update').status_code == 403
    assert client.post('/post/1/delete').status_code == 403
    # current user doesn't see edit link
    assert b'href="/1/update"' not in client.get('/').data


@pytest.mark.parametrize('path', (
    '/post/2/update',
    '/post/2/delete',
))
def test_exists_required(client, auth, path):
    auth.login()
    assert client.post(path).status_code == 404


def test_create(client, auth, app):
    auth.login()
    assert client.get('/post/create').status_code == 200
    client.post('/post/create', data={'title': 'created', 'body': ''})

    with app.app_context():
        db = get_db()
        count = db.execute('SELECT COUNT(id) FROM post').fetchone()[0]
        assert count == 2


def test_update(client, auth, app):
    auth.login()
    assert client.get('/post/1/update').status_code == 200
    client.post('/post/1/update', data={'title': 'updated', 'body': ''})

    with app.app_context():
        db = get_db()
        post = db.execute('SELECT * FROM post WHERE id = 1').fetchone()
        assert post['title'] == 'updated'


@pytest.mark.parametrize('path', (
    '/post/create',
    '/post/1/update',
))
def test_create_update_validate(client, auth, path):
    auth.login()
    response = client.post(path, data={'title': '', 'body': ''})
    assert b'Title is required.' in response.data


def test_delete(client, auth, app):
    auth.login()
    response = client.post('/post/1/delete')
    assert response.headers["Location"] == "/"

    with app.app_context():
        db = get_db()
        post = db.execute('SELECT * FROM post WHERE id = 1').fetchone()
        assert post is None


def test_reaction_clicked(client, auth, app):

    auth.login()
    response = client.get('/post/1/react')
    post = client.get('/post/1')
    assert b"fa fa-thumbs-up fa-clicked" in post.data
    assert b'success' in response.data

    with app.app_context():
        db = get_db()
        reaction = db.execute(
            'SELECT r.id, r.author_id AS author_id, r.post_id AS post_id'
            ' FROM reaction r'
            ' LEFT JOIN user u ON r.author_id = u.id'
            ' LEFT JOIN post p ON r.post_id = p.id'
            ' WHERE p.id = 1',
        ).fetchone()
        assert reaction is not None


def test_reaction_unclicked(client, auth, app):
    auth.login()
    response = client.get('/post/1/unreact')
    post = client.get('/post/1')
    assert b"fa fa-thumbs-up fa-clicked" not in post.data
    assert b'success' in response.data
    with app.app_context():
        db = get_db()
        reaction = db.execute(
            'SELECT r.id, r.author_id AS author_id, r.post_id AS post_id'
            ' FROM reaction r'
            ' LEFT JOIN user u ON r.author_id = u.id'
            ' LEFT JOIN post p ON r.post_id = p.id'
            ' WHERE p.id = 1',
        ).fetchone()
        assert reaction is None


def test_react_path_notloggedin(client):
    response = client.get('/post/1/react')
    assert b"Redirecting" in response.data
