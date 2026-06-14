#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图表在线生成器 - 启动入口"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.server import main

if __name__ == "__main__":
    main()
