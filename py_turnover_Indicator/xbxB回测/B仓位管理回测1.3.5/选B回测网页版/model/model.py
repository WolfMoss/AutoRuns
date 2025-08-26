# -*- coding: utf-8 -*-
"""
回测网页版 | 邢不行 | 2025分享会
author: 邢不行
微信: xbx6660
"""

from typing import Optional, Any

from pydantic import BaseModel


class ResponseModel(BaseModel):
    msg: str = "success"
    code: int = 200
    data: Optional[Any] = None

    @classmethod
    def ok(cls, data: Any = None, msg: str = "success", code: int = 200):
        return cls(msg=msg, code=code, data=data)

    @classmethod
    def error(cls, msg: str = "error", code: int = 400):
        return cls(msg=msg, code=code, data=None)

    @classmethod
    def fail(cls, msg: str = "error", code: int = 500):
        return cls(msg=msg, code=code, data=None)


class ProductInfo(BaseModel):
    product_name: str
    display_name: Optional[str] = None
    dataContentTime: Optional[str] = None
    lastUpdateTime: Optional[str] = None
    full_status: Optional[str] = None
    update_status: Optional[str] = None

    @property
    def product_daily_name(self):
        return self.product_name + '-daily'

    @classmethod
    def dict_to_product_info(cls, d) -> 'ProductInfo':
        """辅助函数，将dict反序列化为ProductInfo对象"""
        if isinstance(d, cls):
            return d
        return cls(**d)
