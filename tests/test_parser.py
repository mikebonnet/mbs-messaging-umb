# Copyright (c) 2017  Red Hat, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Written by Mike Bonnet <mikeb@redhat.com>

from copy import deepcopy
from mock import patch, MagicMock, Mock
from mbs_messaging_umb.parser import CustomParser


# A horrible hack to avoid MBS from detecting pytest is running and using a
# test configuration that is not available as part of the RPM. See
# `module_build_service.config.init_config` for more information.
with patch('sys.argv'):
    import module_build_service.messaging
    from module_build_service.messaging import KojiRepoChange


class TestCustomParser(object):

    repo_msg = {
        'topic': '/topic/VirtualTopic.koji.repo.done',
        'headers': {
            'message-id': 'a1b2c3d4'
        },
        'msg': {
            'repo': {
                'tag_name': 'tag1'
            },
        },
    }

    repo_mapping = {
        'KojiRepoChange': {
            'matches': ['/topic/VirtualTopic.koji.repo.done'],
            'topic': 'topic',
            'msg_id': 'headers.message-id',
            'repo_tag': 'msg.repo.tag_name',
        },
        'GreenwaveDecisionUpdate': {
            'matches': ['/topic/VirtualTopic.eng.greenwave.decision.update'],
            'topic': 'topic',
            'msg_id': 'headers.message-id',
            'decision_context': 'body.msg.decision_context',
            'subject_identifier': 'body.msg.subject_identifier',
            'policies_satisfied': 'body.msg.policies_satisfied'
        },
    }

    @patch('mbs_messaging_umb.parser.load_config')
    def setup_method(self, test_method, load_conf):
        load_conf.return_value = MagicMock(message_mapping=deepcopy(self.repo_mapping))
        self.parser = CustomParser()

    def test_koji_repo_msg(self):
        msg = self.parser.parse(self.repo_msg)
        assert isinstance(msg, KojiRepoChange)
        assert msg.msg_id == self.repo_msg['headers']['message-id']
        assert msg.repo_tag == self.repo_msg['msg']['repo']['tag_name']

        # make sure it works when 'matches' is a string too
        self.parser.conf.message_mapping['KojiRepoChange']['matches'] \
            = '/topic/VirtualTopic.koji.repo.done'
        msg = self.parser.parse(self.repo_msg)
        assert isinstance(msg, KojiRepoChange)
        assert msg.msg_id == self.repo_msg['headers']['message-id']
        assert msg.repo_tag == self.repo_msg['msg']['repo']['tag_name']

    def test_koji_repo_msg_wildcard(self):
        self.parser.conf.message_mapping['KojiRepoChange']['matches'] = [
            '/topic/VirtualTopic.koji.repo.*'
        ]
        msg = self.parser.parse(self.repo_msg)
        assert isinstance(msg, KojiRepoChange)
        assert msg.msg_id == self.repo_msg['headers']['message-id']
        assert msg.repo_tag == self.repo_msg['msg']['repo']['tag_name']

    def test_koji_repo_msg_noattrs(self):
        repo_msg = {
            'topic': '/topic/VirtualTopic.koji.repo.done',
        }
        msg = self.parser.parse(repo_msg)
        assert isinstance(msg, KojiRepoChange)
        assert msg.msg_id is None
        assert msg.repo_tag is None

    def test_koji_repo_msg_no_topic_mapping(self):
        del self.parser.conf.message_mapping['KojiRepoChange']['topic']
        msg = self.parser.parse(self.repo_msg)
        assert msg is None

    def test_koji_repo_msg_no_matches_mapping(self):
        del self.parser.conf.message_mapping['KojiRepoChange']['matches']
        msg = self.parser.parse(self.repo_msg)
        assert msg is None

    def test_koji_repo_msg_no_topic(self):
        repo_msg = self.repo_msg.copy()
        del repo_msg['topic']
        msg = self.parser.parse(repo_msg)
        assert msg is None

    def test_koji_repo_msg_nomatch(self):
        self.parser.conf.message_mapping['KojiRepoChange']['matches'] = [
            '/topic/VirtualTopic.koji.repo.foo'
        ]
        msg = self.parser.parse(self.repo_msg)
        assert msg is None

    def test_koji_repo_msg_noclass(self):
        self.parser.conf.message_mapping['FooBar'] \
            = self.parser.conf.message_mapping['KojiRepoChange']
        del self.parser.conf.message_mapping['KojiRepoChange']
        msg = self.parser.parse(self.repo_msg)
        assert msg is None

    def test_koji_repo_msg_incorrect_params(self):
        repo_msg = deepcopy(self.repo_msg)
        repo_msg['msg']['foo'] = 'bar'
        self.parser.conf.message_mapping['KojiRepoChange']['foo'] \
            = 'msg.foo'
        msg = self.parser.parse(repo_msg)
        assert msg is None

    def test_parse_greenwave_decision_update_msg(self):
        klass = Mock(name='GreenwaveDecisionUpdate')
        with patch.object(module_build_service.messaging,
                          'GreenwaveDecisionUpdate', new=klass, create=True):
            self.parser.parse({
                'topic': '/topic/VirtualTopic.eng.greenwave.decision.update',
                'headers': {'message-id': 'msg-id-1'},
                'body': {
                    'msg': {
                        'decision_context': 'osci_compose_gate_modules',
                        'subject_identifier': 'pkg-1.0-1.c1',
                        'policies_satisfied': True,
                    }
                }
            })

        klass.assert_called_once_with(**{
            'msg_id': 'msg-id-1',
            'decision_context': 'osci_compose_gate_modules',
            'subject_identifier': 'pkg-1.0-1.c1',
            'policies_satisfied': True,
        })
