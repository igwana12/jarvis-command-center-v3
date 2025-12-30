"""
Compression Middleware for Jarvis Command Center V2
Provides intelligent response compression with Brotli and Gzip support
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
import gzip
import brotli
import json
from typing import Callable


class CompressionMiddleware(BaseHTTPMiddleware):
    """Intelligent compression middleware with format negotiation"""

    def __init__(
        self,
        app,
        minimum_size: int = 1000,
        compression_level: int = 6,
        enable_brotli: bool = True,
        enable_gzip: bool = True
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level
        self.enable_brotli = enable_brotli
        self.enable_gzip = enable_gzip

        # Content types that should be compressed
        self.compressible_types = {
            'application/json',
            'application/javascript',
            'text/html',
            'text/css',
            'text/plain',
            'text/xml',
            'application/xml'
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and compress response if applicable"""
        response = await call_next(request)

        # Skip if already compressed
        if 'content-encoding' in response.headers:
            return response

        # Check if response should be compressed
        content_type = response.headers.get('content-type', '').split(';')[0]
        if not any(ct in content_type for ct in self.compressible_types):
            return response

        # Get accepted encodings
        accept_encoding = request.headers.get('accept-encoding', '').lower()

        # Read response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Only compress if meets minimum size
        if len(body) < self.minimum_size:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )

        # Try Brotli first (better compression)
        if self.enable_brotli and 'br' in accept_encoding:
            compressed = brotli.compress(
                body,
                quality=self.compression_level
            )

            return Response(
                content=compressed,
                status_code=response.status_code,
                headers={
                    **dict(response.headers),
                    'content-encoding': 'br',
                    'content-length': str(len(compressed)),
                    'vary': 'Accept-Encoding'
                },
                media_type=response.media_type
            )

        # Fall back to Gzip
        elif self.enable_gzip and 'gzip' in accept_encoding:
            compressed = gzip.compress(
                body,
                compresslevel=self.compression_level
            )

            return Response(
                content=compressed,
                status_code=response.status_code,
                headers={
                    **dict(response.headers),
                    'content-encoding': 'gzip',
                    'content-length': str(len(compressed)),
                    'vary': 'Accept-Encoding'
                },
                media_type=response.media_type
            )

        # No compression
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )


class AdaptiveCompressionMiddleware(BaseHTTPMiddleware):
    """Adaptive compression that adjusts based on content size and type"""

    def __init__(self, app):
        super().__init__(app)

        # Compression strategies by size
        self.strategies = [
            {'min': 0, 'max': 1000, 'method': None, 'level': 0},        # No compression
            {'min': 1000, 'max': 10000, 'method': 'gzip', 'level': 3},  # Fast compression
            {'min': 10000, 'max': 100000, 'method': 'gzip', 'level': 6}, # Balanced
            {'min': 100000, 'max': float('inf'), 'method': 'brotli', 'level': 9} # Maximum
        ]

    def _get_strategy(self, size: int) -> dict:
        """Select compression strategy based on content size"""
        for strategy in self.strategies:
            if strategy['min'] <= size < strategy['max']:
                return strategy
        return self.strategies[0]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process with adaptive compression"""
        response = await call_next(request)

        if 'content-encoding' in response.headers:
            return response

        content_type = response.headers.get('content-type', '').split(';')[0]

        # Only compress JSON and text
        if 'json' not in content_type and 'text' not in content_type:
            return response

        accept_encoding = request.headers.get('accept-encoding', '').lower()
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Select strategy
        strategy = self._get_strategy(len(body))

        if not strategy['method']:
            # No compression
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )

        # Apply compression
        if strategy['method'] == 'brotli' and 'br' in accept_encoding:
            compressed = brotli.compress(body, quality=strategy['level'])
            encoding = 'br'
        elif strategy['method'] == 'gzip' and 'gzip' in accept_encoding:
            compressed = gzip.compress(body, compresslevel=strategy['level'])
            encoding = 'gzip'
        else:
            # Fallback to uncompressed
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )

        return Response(
            content=compressed,
            status_code=response.status_code,
            headers={
                **dict(response.headers),
                'content-encoding': encoding,
                'content-length': str(len(compressed)),
                'vary': 'Accept-Encoding',
                'x-original-size': str(len(body)),
                'x-compression-ratio': f"{len(compressed)/len(body)*100:.1f}%"
            },
            media_type=response.media_type
        )


def get_compression_stats(original_size: int, compressed_size: int) -> dict:
    """Calculate compression statistics"""
    ratio = (compressed_size / original_size) if original_size > 0 else 0
    savings = original_size - compressed_size
    savings_percent = (savings / original_size * 100) if original_size > 0 else 0

    return {
        "original_size": original_size,
        "compressed_size": compressed_size,
        "compression_ratio": round(ratio, 3),
        "savings_bytes": savings,
        "savings_percent": round(savings_percent, 2)
    }
