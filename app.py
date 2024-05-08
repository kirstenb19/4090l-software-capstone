from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus, urlencode
from flask import Flask, request, jsonify, redirect, render_template, request, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm.exc import NoResultFound
from authlib.integrations.flask_client import OAuth
from db import Post, User, user_like_association, user_dislike_association, Comment
import secrets
import os
from sqlalchemy.orm.exc import NoResultFound


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.secret_key = secrets.token_urlsafe(16)
"""
"""

Base = declarative_base()
engine = create_engine('sqlite:///site.db')
Session = sessionmaker(bind=engine)

db = SQLAlchemy(app)    

Base.metadata.create_all(engine, checkfirst=True)

oauth = OAuth(app)

oauth.register(
        "auth0",
        client_id="kMehFewqaxeoWnmDEjdQRLQlQzpzzkCe",
        client_secret="1nQqMP5Cghh9BsjQIaMUUvhEeNuXkrx95MWap2y60rlj9VrDy6frD2uN5QkJ61lw",
        client_kwargs={"scope": "openid profile email",},
        server_metadata_url="https://dev-fkmst0p3l8ckzcn1.us.auth0.com/.well-known/openid-configuration"
)

def is_admin(user_id, db_session):
    """ Checks if a user is an admin """
    user = db_session.query(User).get(user_id)
    return user and user.isAdmin

@app.route('/')
def home():
    user_info = session.get("user")
    if user_info:
        user_id = user_info.get("sub")
        username = user_info.get("nickname")
    else:
        user_id = 0
        username = 'guest'
    db_session = Session()
    posts = db_session.query(Post).outerjoin(Comment).order_by(Post.date_posted.desc()).all()
    db_session.close()
    return render_template('home.html', posts=posts, user_id=user_id, username=username)

@app.route("/callback",methods=["GET","POST"])
def callback():
    """ Auth0 Callback route """
    token = oauth.auth0.authorize_access_token()
    nonce = session["nonce"]
    userinfo = oauth.auth0.parse_id_token(token, nonce)
    session["user"] = userinfo

    db_session = Session()
    user = db_session.query(User).filter_by(id=userinfo["sub"]).first()
    if user is None:
        username = userinfo["nickname"] if "nickname" in userinfo else "Unknown"
        user = User(id=userinfo["sub"], username=username, aboutMe='About Me', email='Enter email here')
        db_session.add(user)
        db_session.commit()

    if user.username == 'christoffelmatthew' or user.username == 'sipenwater':
        user.isAdmin = True
        db_session.commit()
    return redirect(url_for('home'))

@app.route('/register')
def register():
    """ To register for the site, redirects to callback """
    nonce = secrets.token_urlsafe(16)
    session["nonce"] = nonce
    return oauth.auth0.authorize_redirect(redirect_uri=url_for("callback",
        _external=True), nonce=nonce)

@app.route('/login')
def login():
    """ To log into the site, redirects to callback """
    nonce = secrets.token_urlsafe(16)
    session["nonce"] = nonce
    return oauth.auth0.authorize_redirect(redirect_uri=url_for("callback",
        _external=True), nonce=nonce)

@app.route("/logout")
def logout():
    """ To log out of the site, redirects the user back to home after """
    session.clear()
    return redirect(
        "https://dev-fkmst0p3l8ckzcn1.us.auth0.com/v2/logout?" + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": 'kMehFewqaxeoWnmDEjdQRLQlQzpzzkCe',
            },
            quote_via=quote_plus,
        )
    )


@app.route('/profile')
def profile():
    user_info = session.get("user")
    if not user_info:
        return redirect(url_for('home'))
    db_session = Session()
    user = db_session.query(User).filter_by(id=user_info["sub"]).first()
    if user:
        updated_about_me = user.aboutMe  # Get the updated About Me
    else:
        return redirect(url_for('home'))  # Handle cases where user is not found
    user_id = user_info.get("sub")
    username = user_info.get("nickname")
    email = user_info.get("email")
    return render_template('profile.html', user_id=user_id, username=username, email=email, aboutMe=updated_about_me)

@app.route('/update_about_me', methods=['POST'])
def update_about_me():
    user_info = session.get("user")
    if not user_info:
        return redirect(url_for('login'))
    
    user_id = user_info.get("sub")
    about_me = request.form['about_me']

    db_session = Session()
    user = db_session.query(User).filter_by(id=user_id).first()
    if user:
        user.aboutMe = about_me
        db_session.commit()
    db_session.close()
    
    return redirect(url_for('profile'))



@app.route('/create_post', methods=['POST', 'GET'])
def create_post():
    if request.method == 'POST':
        db_session = Session()
        post_title = request.form['title']
        post_url = request.form['url']
        post_content = request.form['content']
        new_post = Post(title=post_title, content=post_content, url=post_url)
        db_session.add(new_post)
        db_session.commit()
        db_session.close()
        return redirect(url_for('home'))
    return render_template('create_post.html')

# @app.route('/post/<int:post_id>/like', methods=['POST'])
# def like_post(post_id):
#     """ Route which disliked a specific post and returns user back to home """
#     user_info = session.get("user")
#     user_id = user_info.get("sub") if user_info else None

#     if user_id and not (has_liked(post_id, user_id) or has_disliked(post_id, user_id)):
#         save_like(post_id, user_id)

#     return redirect(url_for('home'))

# @app.route('/post/<int:post_id>/dislike', methods=['POST'])
# def dislike_post(post_id):
#     """ Route which disliked a specific post and returns user back to home """
#     user_info = session.get("user")
#     user_id = user_info.get("sub") if user_info else None

#     if user_id and not (has_disliked(post_id, user_id) or has_liked(post_id, user_id)):
#         save_dislike(post_id, user_id)

#     return redirect(url_for('home'))

@app.route('/post/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_info = session.get("user")
    user_id = user_info.get("sub")
    db_session = Session()

    post = db_session.query(Post).get(post_id)
    if not post:
        db_session.close()
        return "Post not found", 404

    # Check if the user has already liked the post
    if has_liked(post_id, user_id):
        # User unlikes the post
        remove_like(post_id, user_id)
        post.likes -= 1
    elif has_disliked(post_id, user_id):
        # Switch from dislike to like
        remove_dislike(post_id, user_id)
        post.dislikes -= 1
        add_like(post_id, user_id)
        post.likes += 1
    else:
        # User likes the post for the first time
        add_like(post_id, user_id)
        post.likes += 1

    db_session.commit()
    db_session.close()
    return redirect(url_for('home'))

@app.route('/post/<int:post_id>/dislike', methods=['POST'])
def dislike_post(post_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_info = session.get("user")
    user_id = user_info.get("sub")
    db_session = Session()

    post = db_session.query(Post).get(post_id)
    if not post:
        db_session.close()
        return "Post not found", 404

    # Check if the user has already disliked the post
    if has_disliked(post_id, user_id):
        # User undislikes the post
        remove_dislike(post_id, user_id)
        post.dislikes -= 1
    elif has_liked(post_id, user_id):
        # Switch from like to dislike
        remove_like(post_id, user_id)
        post.likes -= 1
        add_dislike(post_id, user_id)
        post.dislikes += 1
    else:
        # User dislikes the post for the first time
        add_dislike(post_id, user_id)
        post.dislikes += 1

    db_session.commit()
    db_session.close()
    return redirect(url_for('home'))

@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    user_info = session.get("user")
    user_id = user_info.get("sub") if user_info else None
    db_session = Session()

    if not is_admin(user_id, db_session):
        abort(403)

    post = db_session.query(Post).get(post_id)

    if post:
        db_session.execute(user_like_association.delete().where(
            user_like_association.c.post_id == post_id))
        db_session.delete(post)
        db_session.commit()

    db_session.close()

    return redirect(url_for('home'))
    
@app.route('/post/<int:post_id>/edit', methods=['GET'])
def show_edit_post_form(post_id):
    db_session = Session()
    try:
        post = db_session.query(Post).filter(Post.id == post_id).one()
    except NoResultFound:
        # Here we manually handle the case where no result is found, equivalent to get_or_404
        return "Post not found", 404  # You can customize the response as needed
    db_session.close()
    return render_template('edit_post.html', post=post)

@app.route('/post/<int:post_id>/edit', methods=['POST'])
def edit_post(post_id):
    db_session = Session()
    post = db_session.query(Post).filter(Post.id == post_id).first()  # Using first() instead of get()
    if not post:
        db_session.close()
        abort(404)  # Manually aborting with a 404 if the post is not found
    post.title = request.form['title']
    post.url = request.form['url']
    post.content = request.form['content']
    db_session.commit()
    db_session.close()
    return redirect(url_for('home'))

def save_like(post_id, user_id):
    """ Saves a like and reflects database changes when a user likes a post """
    db_session = Session()
    existing_like = has_liked(post_id, user_id)

    if not existing_like:
        like_association = user_like_association.insert().values(
                user_id=user_id, post_id=post_id)
        db_session.execute(like_association)
        db_session.commit()

        post = db_session.query(Post).get(post_id)

        if post:
            post.likes += 1
            db_session.commit()

    db_session.close()



def save_dislike(post_id, user_id):
    """ Updates the DB with new values if a user dislikes a post """
    db_session = Session()

    existing_dislike = has_disliked(post_id, user_id)
    if not existing_dislike:

        dislike_association = user_dislike_association.insert().values(
                user_id=user_id, post_id=post_id)
        db_session.execute(dislike_association)
        db_session.commit()

        post = db_session.query(Post).get(post_id)
        if post:
            post.dislikes += 1
            db_session.commit()

    db_session.close()

# def has_liked(post_id, user_id):
#     """ Checks if a user has already liked a specific post """
#     db_session = Session()
#     like_association = user_like_association.alias()

#     result = db_session.query(like_association.c.post_id)\
#         .filter(like_association.c.user_id == user_id,
#                     like_association.c.post_id == post_id)\
#         .first()

#     db_session.close()
#     return result is not None
    


# def has_disliked(post_id, user_id):
#     """ Checks if a user has already disliked a specific post """
#     db_session = Session()
    
#     dislike_association = user_dislike_association.alias()

#     result = db_session.query(dislike_association.c.post_id)\
#             .filter(dislike_association.c.user_id == user_id,
#                     dislike_association.c.post_id == post_id)\
#             .first()
    
#     db_session.close()
#     return result is not None

def has_liked(post_id, user_id):
    db_session = Session()
    result = db_session.query(user_like_association)\
        .filter(user_like_association.c.user_id == user_id,
                user_like_association.c.post_id == post_id)\
        .first()
    db_session.close()
    return result is not None
    

def has_disliked(post_id, user_id):
    db_session = Session()
    result = db_session.query(user_dislike_association)\
        .filter(user_dislike_association.c.user_id == user_id,
                user_dislike_association.c.post_id == post_id)\
        .first()
    db_session.close()
    return result is not None

def add_like(post_id, user_id):
    db_session = Session()
    like_association = user_like_association.insert().values(user_id=user_id, post_id=post_id)
    db_session.execute(like_association)
    db_session.commit()
    db_session.close()

def remove_like(post_id, user_id):
    db_session = Session()
    db_session.execute(user_like_association.delete().where(
        user_like_association.c.user_id == user_id,
        user_like_association.c.post_id == post_id))
    db_session.commit()
    db_session.close()

def add_dislike(post_id, user_id):
    db_session = Session()
    dislike_association = user_dislike_association.insert().values(user_id=user_id, post_id=post_id)
    db_session.execute(dislike_association)
    db_session.commit()
    db_session.close()

def remove_dislike(post_id, user_id):
    db_session = Session()
    db_session.execute(user_dislike_association.delete().where(
        user_dislike_association.c.user_id == user_id,
        user_dislike_association.c.post_id == post_id))
    db_session.commit()
    db_session.close()


@app.route('/post/<int:post_id>/comment', methods=['POST'])
def post_comment(post_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db_session = Session()
    try:
        post = db_session.query(Post).filter(Post.id == post_id).one()
    except NoResultFound:
        # Here we manually handle the case where no result is found, equivalent to get_or_404
        return "Post not found", 404  # You can customize the response as needed
    comment_content = request.form['comment']
    user_id = session['user']['sub']
    comment = Comment(content=comment_content, user_id=user_id, post_id=post_id)
    db_session.add(comment)
    db_session.commit()
    db_session.close()
    return redirect(url_for('home'))

@app.route('/post/<int:post_id>')
def show_post(post_id):
    db_session = Session()
    post = db_session.query(Post).filter(Post.id == post_id).first()
    if not post:
        db_session.close()
        abort(404)  # Manually aborting with a 404 if the post is not found
    comments = db_session.query(Comment).filter_by(post_id=post_id).all()
    db_session.close()
    return render_template('post.html', post=post, comments=comments)



@app.route('/search')
def search_results():
    query = request.args.get('query')
    if not query:
        return redirect(url_for('home'))

    db_session = Session()
    # Using `ilike` for case-insensitive search; adjust the filtering logic as needed
    results = db_session.query(Post).filter(Post.title.ilike(f'%{query}%')).all()
    db_session.close()
    return render_template('search_results.html', posts=results, query=query)

if __name__ ==  '__main__':
	app.run(debug=True)
