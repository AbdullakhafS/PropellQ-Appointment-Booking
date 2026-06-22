using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Options;

namespace PropelIQ.Infrastructure.Security;

/// <summary>
/// AES-256-GCM symmetric encryption for HIPAA-compliant transcript storage.
/// Key is loaded from configuration and never persisted in plaintext.
/// </summary>
public sealed class TranscriptEncryption
{
    private readonly byte[] _key;

    public TranscriptEncryption(IOptions<TranscriptEncryptionOptions> options)
    {
        var base64Key = options.Value.EncryptionKey;
        if (string.IsNullOrEmpty(base64Key))
            throw new InvalidOperationException("Transcript encryption key is not configured.");

        _key = Convert.FromBase64String(base64Key);
        if (_key.Length != 32)
            throw new InvalidOperationException("Encryption key must be 256 bits (32 bytes) encoded as Base64.");
    }

    public string Encrypt(string plaintext)
    {
        var plaintextBytes = Encoding.UTF8.GetBytes(plaintext);
        var nonce = RandomNumberGenerator.GetBytes(AesGcm.NonceByteSizes.MaxSize);
        var ciphertext = new byte[plaintextBytes.Length];
        var tag = new byte[AesGcm.TagByteSizes.MaxSize];

        using var aes = new AesGcm(_key, AesGcm.TagByteSizes.MaxSize);
        aes.Encrypt(nonce, plaintextBytes, ciphertext, tag);

        // Format: base64(nonce) + "." + base64(tag) + "." + base64(ciphertext)
        return $"{Convert.ToBase64String(nonce)}.{Convert.ToBase64String(tag)}.{Convert.ToBase64String(ciphertext)}";
    }

    public string Decrypt(string encryptedValue)
    {
        var parts = encryptedValue.Split('.');
        if (parts.Length != 3)
            throw new FormatException("Invalid encrypted transcript format.");

        var nonce = Convert.FromBase64String(parts[0]);
        var tag = Convert.FromBase64String(parts[1]);
        var ciphertext = Convert.FromBase64String(parts[2]);
        var plaintext = new byte[ciphertext.Length];

        using var aes = new AesGcm(_key, AesGcm.TagByteSizes.MaxSize);
        aes.Decrypt(nonce, ciphertext, tag, plaintext);

        return Encoding.UTF8.GetString(plaintext);
    }
}

public sealed class TranscriptEncryptionOptions
{
    public const string SectionName = "TranscriptEncryption";

    /// <summary>Base64-encoded 256-bit AES key. Load from Key Vault or environment variable.</summary>
    public string EncryptionKey { get; init; } = string.Empty;
}
