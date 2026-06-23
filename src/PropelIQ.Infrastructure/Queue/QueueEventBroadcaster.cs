using System.Runtime.CompilerServices;
using System.Threading.Channels;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Infrastructure.Queue;

/// <summary>
/// Union wrapper for the SSE broadcast channel.
/// Carries either a standard QueueEvent or a QueueReorderEvent.
/// </summary>
public sealed record QueueBroadcastMessage(
    QueueEvent? Event,
    QueueReorderEvent? ReorderEvent
)
{
    public static QueueBroadcastMessage FromEvent(QueueEvent e) => new(e, null);
    public static QueueBroadcastMessage FromReorder(QueueReorderEvent r) => new(null, r);
}

/// <summary>
/// In-process broadcast hub using System.Threading.Channels.
/// Each SSE subscriber gets a bounded channel; events are fan-out published to all channels.
/// Channels are bounded to prevent memory build-up if a client is slow.
/// </summary>
public sealed class QueueEventBroadcaster : IQueueEventBroadcaster
{
    private readonly object _lock = new();
    private readonly List<Channel<QueueBroadcastMessage>> _channels = [];

    public int ActiveConnections
    {
        get { lock (_lock) return _channels.Count; }
    }

    public void Publish(QueueEvent queueEvent)
        => FanOut(QueueBroadcastMessage.FromEvent(queueEvent));

    public void PublishReorder(QueueReorderEvent reorderEvent)
        => FanOut(QueueBroadcastMessage.FromReorder(reorderEvent));

    private void FanOut(QueueBroadcastMessage message)
    {
        List<Channel<QueueBroadcastMessage>> snapshot;
        lock (_lock) { snapshot = [.. _channels]; }

        foreach (var channel in snapshot)
            channel.Writer.TryWrite(message);
    }

    public async IAsyncEnumerable<QueueEvent> SubscribeAsync(
        [EnumeratorCancellation] CancellationToken ct)
    {
        // Backwards-compat: yield only non-reorder events.
        await foreach (var msg in SubscribeAllAsync(ct))
            if (msg.Event is { } e)
                yield return e;
    }

    /// <summary>Full stream including reorder events; used by the SSE controller.</summary>
    public async IAsyncEnumerable<QueueBroadcastMessage> SubscribeAllAsync(
        [EnumeratorCancellation] CancellationToken ct)
    {
        var channel = Channel.CreateBounded<QueueBroadcastMessage>(
            new BoundedChannelOptions(64)
            {
                FullMode = BoundedChannelFullMode.DropOldest,
                SingleReader = true,
                SingleWriter = false,
            });

        lock (_lock) { _channels.Add(channel); }

        try
        {
            await foreach (var msg in channel.Reader.ReadAllAsync(ct))
                yield return msg;
        }
        finally
        {
            lock (_lock) { _channels.Remove(channel); }
            channel.Writer.TryComplete();
        }
    }
}
