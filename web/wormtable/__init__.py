#
# Copyright (C) 2013, wormtable developers (see AUTHORS.txt).
#
# This file is part of wormtable.
#
# Wormtable is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Wormtable is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wormtable.  If not, see <http://www.gnu.org/licenses/>.
#

__version__ = '0.1.5a2'

from .tables import *  # NOQA
from .vcf2wt import vcf2wt_main
from .gtf2wt import gtf2wt_main
from .wtadmin import wtadmin_main
