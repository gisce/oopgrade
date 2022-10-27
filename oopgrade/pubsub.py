# encoding: utf-8
def send_msg(redis_url, secret, channel, msg):
    from itsdangerous import Signer
    from redis import from_url
    s = Signer(secret)
    signed_msg = s.sign(msg)
    redis_conn = from_url(redis_url)
    sent_to = redis_conn.publish(channel, signed_msg)
    return sent_to
