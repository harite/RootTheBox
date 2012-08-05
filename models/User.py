# -*- coding: utf-8 -*-
'''
Created on Mar 12, 2012

@author: moloch

    Copyright [2012] [Redacted Labs]

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''


import logging

from string import ascii_letters, digits, printable
from hashlib import md5, sha256
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import synonym, relationship, backref
from sqlalchemy.types import Unicode, Integer, Boolean
from libs.ConfigManager import ConfigManager
from models import dbsession, association_table
from models.Box import Box
from models.Team import Team
from models.Permission import Permission
from models.Notification import Notification
from models.BaseGameObject import BaseObject


class User(BaseObject):
    ''' User definition '''

    _account = Column(Unicode(64), unique=True, nullable=False)
    account = synonym('_account', descriptor=property(
        lambda self: self._account,
        lambda self, account: setattr(
            self, '_account', self.__class__.filter_string(account, " _-"))
    ))
    _handle = Column(Unicode(64), unique=True, nullable=False)
    handle = synonym('_handle', descriptor=property(
        lambda self: self._handle,
        lambda self, handle: setattr(
            self, '_handle', self.__class__.filter_string(handle, " _-"))
    ))
    team_id = Column(Integer, ForeignKey('team.id'))
    pastes = relationship("PasteBin", backref=backref("User", lazy="joined"), cascade="all, delete-orphan")
    permissions = relationship("Permission", backref=backref("User", lazy="joined"), cascade="all, delete-orphan")
    notifications = relationship("Notification", backref=backref("User", lazy="joined"), cascade="all, delete-orphan")
    avatar = Column(Unicode(64), default=unicode("default_avatar.jpeg"))
    _password = Column('password', Unicode(128))
    password = synonym('_password', descriptor=property(
        lambda self: self._password,
        lambda self, password: setattr(
            self, '_password', self.__class__._hash_password(password))
    ))

    @property
    def permissions(self):
        '''Return a set with all permissions granted to the user.'''
        return dbsession.query(Permission).filter_by(user_id=self.id)

    @property
    def permissions_accounts(self):
        '''Return a list with all permissions accounts granted to the user.'''
        return [permission.account for permission in self.permissions]

    @property
    def team_name(self):
        ''' Return a list with all groups accounts the user is a member of '''
        if self.team_id == None:
            return None
        else:
            team = dbsession.query(
                Team).filter_by(id=self.team_id).first()
            return team.account

    @property
    def team(self):
        ''' Return a the uesr's team object '''
        if self.team_id == None:
            return None
        else:
            return dbsession.query(Team).filter_by(id=self.team_id).first()

    @classmethod
    def get_all(cls):
        ''' Return all non-admin user objects '''
        return dbsession.query(cls).filter(cls.user_account != 'admin').all()

    @classmethod
    def get_free_agents(cls):
        ''' Return all non-admin user objects without a team '''
        return dbsession.query(cls).filter_by(team_id=None).filter(cls.user_account != 'admin').all()

    @classmethod
    def by_account(cls, account):
        ''' Return the user object whose user account is "account" '''
        return dbsession.query(cls).filter_by(account=unicode(account)).first()

    @classmethod
    def by_handle(cls, handle):
        ''' Return the user object whose user account is "handle" '''
        return dbsession.query(cls).filter_by(handle=unicode(handle)).first()

    @classmethod
    def by_id(cls, user_id):
        ''' Return the user object whose user id is "user_id" '''
        return dbsession.query(cls).filter_by(id=user_id).first()

    @classmethod
    def add_to_team(cls, team_account):
        ''' Add user to team based on team account '''
        team = dbsession.query(Team).filter_by(account=unicode(team_account)).first()
        cls.team_id = team.id

    @classmethod
    def _hash_password(cls, password):
        ''' Hashes the password using Md5/Sha256 :D '''
        config = ConfigManager.Instance()
        password = filter(lambda char: char in printable[:-5], password)
        if config.max_password_length <= len(password):
            password = cls.admin_hash(password)
        else:
            password = cls.user_hash(password)
        return password

    @classmethod
    def filter_string(cls, string, extra_chars=''):
        char_white_list = ascii_letters + digits + extra_chars
        return filter(lambda char: char in char_white_list, string)

    @classmethod
    def user_hash(cls, preimage):
        ''' Single round md5 '''
        md5_hash = md5()
        md5_hash.update(preimage)
        return unicode(md5_hash.hexdigest())

    @classmethod
    def admin_hash(cls, preimage):
        ''' 25,000 rounds of sha256 '''
        sha_hash = sha256()
        sha_hash.update(preimage)
        for count in range(1, 25000):
            sha_hash.update(preimage + sha_hash.hexdigest() + str(count))
        return unicode(sha_hash.hexdigest())

    def has_permission(self, permission):
        ''' Return True if 'permission' is in permissions_accounts '''
        return True if permission in self.permissions_accounts else False

    def validate_password(self, attempt):
        ''' Check the password against existing credentials '''
        attempt = filter(lambda char: char in string.printable[:-5], attempt)
        if isinstance(attempt, unicode):
            attempt = attempt.encode('utf-8')
        if self.has_permission('admin'):
            return self.password == self.admin_hash(attempt)
        else:
            return self.password == self.user_hash(unicode(attempt))

    def get_new_notifications(self):
        ''' Returns any unread messages '''
        return filter(lambda notification: notification.viewed == False, self.notifications)

    def get_notifications(self, limit=10):
        ''' Return most recent notifications '''
        return sorted(self.notifications[:limit])

    def __repr__(self):
        return ('<User - account: %s, display: %s, team_id: %d>' % (self.user_account, self.handle, self.team_id)).encode('utf-8')
