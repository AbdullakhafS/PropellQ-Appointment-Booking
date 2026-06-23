using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PropelIQ.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddConversationStage : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "CurrentStage",
                table: "IntakeConversations",
                type: "int",
                nullable: false,
                defaultValue: 0);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "CurrentStage",
                table: "IntakeConversations");
        }
    }
}
