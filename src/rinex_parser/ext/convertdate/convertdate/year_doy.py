#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file can be part of converdate.
# https://github.com/fitnr/convertdate

# Licensed under the MIT license:
# http://opensource.org/licenses/MIT
# Copyright (c) 2018, jiargei <contact@messfuchs.at>

import datetime


def to_datetime(year, day_of_year):
    '''Creates a Datetime Object from Year and DayofYear. Time set to default'''
    return datetime.datetime(
        year, 1, 1) + datetime.timedelta(day_of_year - 1)


def from_datetime(date_time):
    '''Extracts Year and Day of Year out of a Datetime or Date object'''
    assert isinstance(date_time, (datetime.datetime, datetime.date))
    year = date_time.year
    day_of_year = date_time.timetuple().tm_yday
    return [year, day_of_year]
