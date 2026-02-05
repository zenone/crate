"""
Streaming Response Utilities for Real-Time Progress

Task #124: Server-Sent Events (SSE) for streaming rename progress

Provides real-time progress updates during long-running operations:
- Stream results as they complete (no buffering)
- EventSource compatible (standard SSE format)
- Can be cancelled mid-stream
- No HTTP timeout issues

Benefits:
- Real-time progress instead of waiting for completion
- Better UX for massive libraries (50K+ files)
- User can see errors immediately
- Can cancel anytime
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """
    Server-Sent Event format.

    SSE format:
    data: {"type": "start", "total": 1000}

    event: progress
    data: {"index": 0, "file": "song.mp3", "status": "renamed"}

    """
    type: str  # Event type: start, progress, complete, error
    data: Dict[str, Any]  # Event data
    event: Optional[str] = None  # Optional event name for EventSource filtering
    id: Optional[str] = None  # Optional event ID for reconnection
    retry: Optional[int] = None  # Optional retry interval in ms

    def format_sse(self) -> str:
        """
        Format as Server-Sent Event string.

        Returns:
            SSE formatted string with double newline

        Examples:
            >>> event = StreamEvent("progress", {"index": 0, "file": "song.mp3"})
            >>> print(event.format_sse())
            data: {"type": "progress", "data": {"index": 0, "file": "song.mp3"}}

        """
        lines = []

        # Event type (optional)
        if self.event:
            lines.append(f"event: {self.event}")

        # Event ID (optional, for reconnection)
        if self.id:
            lines.append(f"id: {self.id}")

        # Retry interval (optional)
        if self.retry:
            lines.append(f"retry: {self.retry}")

        # Data (required)
        event_data = {
            "type": self.type,
            **self.data
        }
        data_json = json.dumps(event_data)
        lines.append(f"data: {data_json}")

        # SSE requires double newline at end
        return '\n'.join(lines) + '\n\n'


async def stream_rename_progress(
    operation_id: str,
    total_files: int,
    renamer_api: Any,
    logger: logging.Logger
) -> AsyncGenerator[str, None]:
    """
    Stream rename operation progress as Server-Sent Events.

    Task #124: Main streaming generator for rename operations.

    Args:
        operation_id: Async operation ID from renamer_api
        total_files: Total number of files to rename
        renamer_api: RenamerAPI instance
        logger: Logger instance

    Yields:
        SSE formatted progress updates

    Examples:
        >>> async for chunk in stream_rename_progress(op_id, 1000, api, logger):
        ...     # chunk is SSE formatted string
        ...     yield chunk
    """
    try:
        # Send start event
        start_event = StreamEvent(
            type="start",
            data={
                "operation_id": operation_id,
                "total": total_files,
                "message": "Rename operation started"
            }
        )
        yield start_event.format_sse()

        # Poll for progress
        last_progress = 0
        while True:
            # Get operation status
            status = renamer_api.get_operation_status(operation_id)

            if status is None:
                # Operation not found
                error_event = StreamEvent(
                    type="error",
                    data={
                        "error": "Operation not found",
                        "operation_id": operation_id
                    }
                )
                yield error_event.format_sse()
                return

            # Send progress update if changed
            if status.progress > last_progress:
                progress_event = StreamEvent(
                    type="progress",
                    event="progress",  # For EventSource filtering
                    data={
                        "operation_id": operation_id,
                        "progress": status.progress,
                        "total": status.total,
                        "percentage": (status.progress / status.total * 100) if status.total > 0 else 0,
                        "current_file": status.current_file or "",
                        "status": status.status
                    }
                )
                yield progress_event.format_sse()
                last_progress = status.progress

            # Check if operation complete
            if status.status in ["completed", "error", "cancelled"]:
                # Send completion event
                complete_event = StreamEvent(
                    type=status.status,
                    event="complete",
                    data={
                        "operation_id": operation_id,
                        "status": status.status,
                        "progress": status.progress,
                        "total": status.total,
                        "results": status.results.to_dict() if status.results else None,
                        "error": status.error
                    }
                )
                yield complete_event.format_sse()
                return

            # Wait before next poll (100ms)
            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        # Client disconnected
        logger.info(f"Stream cancelled for operation {operation_id}")

        # Try to cancel operation
        renamer_api.cancel_operation(operation_id)

        # Send cancellation event
        cancel_event = StreamEvent(
            type="cancelled",
            data={
                "operation_id": operation_id,
                "message": "Operation cancelled by client disconnect"
            }
        )
        yield cancel_event.format_sse()

    except Exception as e:
        logger.error(f"Error streaming progress for operation {operation_id}: {e}", exc_info=True)

        # Send error event
        error_event = StreamEvent(
            type="error",
            data={
                "operation_id": operation_id,
                "error": str(e),
                "message": "Internal server error"
            }
        )
        yield error_event.format_sse()


async def stream_metadata_loading(
    files: list,
    renamer_api: Any,
    logger: logging.Logger,
    enhance_metadata: bool = False
) -> AsyncGenerator[str, None]:
    """
    Stream metadata loading progress.

    For directories with thousands of files, stream progress as metadata loads.

    Args:
        files: List of files to load metadata for
        renamer_api: RenamerAPI instance
        logger: Logger instance
        enhance_metadata: If True, run audio analysis (slow)

    Yields:
        SSE formatted progress updates
    """
    try:
        total = len(files)

        # Send start event
        start_event = StreamEvent(
            type="start",
            data={
                "total": total,
                "enhance_metadata": enhance_metadata,
                "message": "Loading metadata..."
            }
        )
        yield start_event.format_sse()

        # Load metadata for each file
        for index, file in enumerate(files):
            # Load metadata
            # (In real implementation, this would call read_mp3_metadata)

            # Send progress
            progress_event = StreamEvent(
                type="progress",
                event="progress",
                data={
                    "index": index,
                    "total": total,
                    "percentage": (index / total * 100) if total > 0 else 0,
                    "current_file": str(file.get('name', '')),
                    "loaded": index + 1
                }
            )
            yield progress_event.format_sse()

            # Brief pause to allow client to process
            if index % 100 == 0:
                await asyncio.sleep(0.01)

        # Send complete event
        complete_event = StreamEvent(
            type="complete",
            event="complete",
            data={
                "total": total,
                "loaded": total,
                "message": "Metadata loading complete"
            }
        )
        yield complete_event.format_sse()

    except asyncio.CancelledError:
        logger.info("Metadata loading stream cancelled")

        cancel_event = StreamEvent(
            type="cancelled",
            data={"message": "Metadata loading cancelled"}
        )
        yield cancel_event.format_sse()

    except Exception as e:
        logger.error(f"Error streaming metadata loading: {e}", exc_info=True)

        error_event = StreamEvent(
            type="error",
            data={"error": str(e), "message": "Failed to load metadata"}
        )
        yield error_event.format_sse()


# Helper for keeping connection alive
async def send_keepalive() -> str:
    """
    Send SSE comment as keepalive.

    Prevents connection timeout on slow networks.

    Returns:
        SSE formatted comment
    """
    return ": keepalive\n\n"


# Batch streaming helper
async def stream_batch_progress(
    batches: list,
    process_batch_callback,
    logger: logging.Logger
) -> AsyncGenerator[str, None]:
    """
    Stream progress for batch processing.

    Useful for massive libraries processed in batches.

    Args:
        batches: List of batches to process
        process_batch_callback: Async callback(batch) -> results
        logger: Logger instance

    Yields:
        SSE formatted batch progress
    """
    total_batches = len(batches)

    # Send start
    start_event = StreamEvent(
        type="start",
        data={
            "total_batches": total_batches,
            "message": "Starting batch processing"
        }
    )
    yield start_event.format_sse()

    # Process each batch
    for batch_index, batch in enumerate(batches):
        # Send batch start
        batch_start_event = StreamEvent(
            type="batch_start",
            data={
                "batch_index": batch_index,
                "total_batches": total_batches,
                "batch_size": len(batch)
            }
        )
        yield batch_start_event.format_sse()

        # Process batch
        try:
            results = await process_batch_callback(batch)

            # Send batch complete
            batch_complete_event = StreamEvent(
                type="batch_complete",
                data={
                    "batch_index": batch_index,
                    "total_batches": total_batches,
                    "results_count": len(results)
                }
            )
            yield batch_complete_event.format_sse()

        except Exception as e:
            logger.error(f"Batch {batch_index} failed: {e}", exc_info=True)

            # Send batch error
            batch_error_event = StreamEvent(
                type="batch_error",
                data={
                    "batch_index": batch_index,
                    "error": str(e)
                }
            )
            yield batch_error_event.format_sse()

    # Send complete
    complete_event = StreamEvent(
        type="complete",
        data={
            "total_batches": total_batches,
            "message": "Batch processing complete"
        }
    )
    yield complete_event.format_sse()
