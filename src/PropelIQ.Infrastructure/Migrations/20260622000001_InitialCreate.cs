using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PropelIQ.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "ChatbotPrompts",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    PromptVersion = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    PromptText = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    EffectiveDate = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    DeprecatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: true)
                },
                constraints: table => table.PrimaryKey("PK_ChatbotPrompts", x => x.Id));

            migrationBuilder.CreateTable(
                name: "IntakeConversations",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    AppointmentId = table.Column<int>(type: "int", nullable: false),
                    PatientId = table.Column<int>(type: "int", nullable: false),
                    Mode = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    Transcript = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    ExtractedData = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    ConfidenceScores = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    MisunderstandingCount = table.Column<int>(type: "int", nullable: false, defaultValue: 0),
                    CompletedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: true),
                    SwitchedToManualAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: true),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table => table.PrimaryKey("PK_IntakeConversations", x => x.Id));

            migrationBuilder.CreateIndex(
                name: "IX_ChatbotPrompts_PromptVersion",
                table: "ChatbotPrompts",
                column: "PromptVersion",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_IntakeConversations_AppointmentId",
                table: "IntakeConversations",
                column: "AppointmentId");

            migrationBuilder.CreateIndex(
                name: "IX_IntakeConversations_PatientId",
                table: "IntakeConversations",
                column: "PatientId");

            migrationBuilder.CreateIndex(
                name: "IX_IntakeConversations_Mode",
                table: "IntakeConversations",
                column: "Mode");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(name: "IntakeConversations");
            migrationBuilder.DropTable(name: "ChatbotPrompts");
        }
    }
}
