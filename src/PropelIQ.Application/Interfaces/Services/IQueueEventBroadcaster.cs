using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

/// <summary>
/// Broadcasts queue events to all currently-connected SSE staff clients.
/// Implemented as a singleton to share state across HTTP request scopes.
/// </summary>
public interface IQueueEventBroadcaster
{
    /// <summary>Registers an SSE response stream; yields events until the client disconnects.</summary>
    IAsyncEnumerable<QueueEvent> SubscribeAsync(CancellationToken ct);

    /// <summary>Publishes a queue event to all subscribers.</summary>
    void Publish(QueueEvent queueEvent);

    /// <summary>Publishes a reorder event (different payload shape) to all subscribers.</summary>
    void PublishReorder(QueueReorderEvent reorderEvent);

    /// <summary>Number of currently active SSE connections.</summary>
    int ActiveConnections { get; }
}
