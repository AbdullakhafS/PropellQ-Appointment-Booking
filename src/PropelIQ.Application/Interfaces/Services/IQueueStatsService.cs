using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

public interface IQueueStatsService
{
    /// <summary>
    /// Computes current queue statistics from live appointment state.
    /// Always returns a result; handles missing timestamps safely.
    /// </summary>
    QueueStats ComputeStats();
}
