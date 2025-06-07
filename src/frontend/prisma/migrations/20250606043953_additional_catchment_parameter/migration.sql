/*
  Warnings:

  - The `isozones_running` column on the `Project` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterTable
ALTER TABLE "Project" ADD COLUMN     "catchment_area" DOUBLE PRECISION NOT NULL DEFAULT 0,
ADD COLUMN     "channel_length" DOUBLE PRECISION NOT NULL DEFAULT 0,
ADD COLUMN     "delta_h" DOUBLE PRECISION NOT NULL DEFAULT 0,
DROP COLUMN "isozones_running",
ADD COLUMN     "isozones_running" BOOLEAN NOT NULL DEFAULT false;
