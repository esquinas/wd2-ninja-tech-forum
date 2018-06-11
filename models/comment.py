from google.appengine.ext import ndb
from google.appengine.api import app_identity, mail, taskqueue

from models.topic_subscription import TopicSubscription
from utils.helpers import escape_html

class Comment(ndb.Model):
    content = ndb.TextProperty()
    author_email = ndb.StringProperty()
    topic_id = ndb.IntegerProperty()
    topic_title = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    deleted = ndb.BooleanProperty(default=False)

    @classmethod
    def create(cls, content, user, topic):
        """Class method to create new comment.

        :param content: Content text
        :type content: str
        :param user: Author user
        :type user: User
        :param topic: Topic where the comment belongs to
        :type topic: Topic
        :return:
        """
        new_comment = cls(
            content=escape_html(content),
            topic_id=topic.key.id(),
            topic_title=topic.title,
            author_email=user.email(),
        )
        new_comment.put()


        subscriptions = TopicSubscription.query(TopicSubscription.topic_id == topic.key.id()).fetch()

        subscribers = [topic.author_email, ]

        for subscription in subscriptions:
            if subscription.user_email != user.email():
                subscribers.append(subscription.user_email)

        # send notification to topic author and subscribers
        for email in subscribers:
            params = {
                'topic-author-email': email,
                'topic-title': topic.title,
                'topic-id': topic.key.id(),
            }
            taskqueue.add(url='/task/email-new-comment', params=params)

        hostname = app_identity.get_default_version_hostname()

        mail.send_mail(
            sender='esquinas.enrique@gmail.com',
                       to=topic.author_email,
                       subject='New comment on your topic',
                       body="""
                           Your topic <strong>{0}</strong> received a new comment!

                           Click <a href="https://{1}/topic/{2}">on this link</a> 
                           to see it.
                           
                           Hostname: {2}
                           """.format(
                           topic.title,
                           hostname,
                           topic.key.id(),
                       )
        )

        return new_comment

    @classmethod
    def delete(cls, comment_id):
        comment = Comment.get_by_id(int(comment_id))
        comment.deleted = True
        comment.put()
        return comment

    # TODO: Implement @classmethod filter_by_topic(cls, topic)
