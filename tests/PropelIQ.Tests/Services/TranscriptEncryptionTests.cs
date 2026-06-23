using Microsoft.Extensions.Options;
using PropelIQ.Infrastructure.Security;
using Xunit;
using FluentAssertions;

namespace PropelIQ.Tests.Services;

public sealed class TranscriptEncryptionTests
{
    private static TranscriptEncryption CreateEncryption()
    {
        // 32-byte key for testing
        var key = Convert.ToBase64String(new byte[32]);
        var opts = Options.Create(new TranscriptEncryptionOptions { EncryptionKey = key });
        return new TranscriptEncryption(opts);
    }

    [Fact]
    public void Encrypt_ThenDecrypt_ReturnsOriginalText()
    {
        var encryption = CreateEncryption();
        var original = """[{"role":"user","content":"I have a headache","timestamp":"2026-06-22T10:00:00Z"}]""";

        var encrypted = encryption.Encrypt(original);
        var decrypted = encryption.Decrypt(encrypted);

        decrypted.Should().Be(original);
    }

    [Fact]
    public void Encrypt_ProducesDifferentCiphertextEachTime()
    {
        var encryption = CreateEncryption();
        var plaintext = "same plaintext";

        var first = encryption.Encrypt(plaintext);
        var second = encryption.Encrypt(plaintext);

        // Due to random nonce, each encryption produces different output
        first.Should().NotBe(second);
    }

    [Fact]
    public void Decrypt_TamperedData_ThrowsException()
    {
        var encryption = CreateEncryption();
        var encrypted = encryption.Encrypt("sensitive data");
        var parts = encrypted.Split('.');
        // Tamper with ciphertext
        var tampered = $"{parts[0]}.{parts[1]}.AAAA";

        var act = () => encryption.Decrypt(tampered);
        act.Should().Throw<Exception>();
    }

    [Fact]
    public void Constructor_InvalidKeyLength_ThrowsInvalidOperationException()
    {
        var shortKey = Convert.ToBase64String(new byte[16]); // 128-bit, not 256-bit
        var opts = Options.Create(new TranscriptEncryptionOptions { EncryptionKey = shortKey });

        var act = () => new TranscriptEncryption(opts);
        act.Should().Throw<InvalidOperationException>().WithMessage("*256 bits*");
    }
}
