using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PropelIQ.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddQueuePersistence : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(@"
IF OBJECT_ID(N'[dbo].[Appointments]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Appointments] (
        [Id] uniqueidentifier NOT NULL,
        [PatientId] uniqueidentifier NOT NULL,
        [PatientFullName] nvarchar(250) NOT NULL,
        [ProviderName] nvarchar(200) NOT NULL,
        [AppointmentTime] datetimeoffset NOT NULL,
        [DurationMinutes] int NOT NULL,
        [IsWalkIn] bit NOT NULL,
        [SlotId] uniqueidentifier NULL,
        [Status] nvarchar(30) NOT NULL,
        [Notes] nvarchar(1000) NULL,
        [CreatedAt] datetimeoffset NOT NULL,
        [ArrivedAt] datetimeoffset NULL,
        CONSTRAINT [PK_Appointments] PRIMARY KEY ([Id])
    );
END;

IF OBJECT_ID(N'[dbo].[Patients]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Patients] (
        [Id] uniqueidentifier NOT NULL,
        [FirstName] nvarchar(100) NOT NULL,
        [LastName] nvarchar(100) NOT NULL,
        [DateOfBirth] date NOT NULL,
        [Phone] nvarchar(50) NOT NULL,
        [Email] nvarchar(320) NULL,
        [Gender] nvarchar(20) NOT NULL,
        [Address] nvarchar(500) NULL,
        [Notes] nvarchar(1000) NULL,
        [CreatedAt] datetimeoffset NOT NULL,
        CONSTRAINT [PK_Patients] PRIMARY KEY ([Id])
    );
END;

IF OBJECT_ID(N'[dbo].[Appointments]', N'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Appointments_AppointmentTime' AND object_id = OBJECT_ID(N'[dbo].[Appointments]'))
        CREATE INDEX [IX_Appointments_AppointmentTime] ON [dbo].[Appointments] ([AppointmentTime]);

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Appointments_PatientId' AND object_id = OBJECT_ID(N'[dbo].[Appointments]'))
        CREATE INDEX [IX_Appointments_PatientId] ON [dbo].[Appointments] ([PatientId]);

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Appointments_ProviderName_AppointmentTime' AND object_id = OBJECT_ID(N'[dbo].[Appointments]'))
        CREATE INDEX [IX_Appointments_ProviderName_AppointmentTime] ON [dbo].[Appointments] ([ProviderName], [AppointmentTime]);
END;

IF OBJECT_ID(N'[dbo].[Patients]', N'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Patients_Email' AND object_id = OBJECT_ID(N'[dbo].[Patients]'))
        CREATE INDEX [IX_Patients_Email] ON [dbo].[Patients] ([Email]);

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Patients_Phone' AND object_id = OBJECT_ID(N'[dbo].[Patients]'))
        CREATE INDEX [IX_Patients_Phone] ON [dbo].[Patients] ([Phone]);
END;
");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(@"
IF OBJECT_ID(N'[dbo].[Appointments]', N'U') IS NOT NULL
    DROP TABLE [dbo].[Appointments];

IF OBJECT_ID(N'[dbo].[Patients]', N'U') IS NOT NULL
    DROP TABLE [dbo].[Patients];
");
        }
    }
}
