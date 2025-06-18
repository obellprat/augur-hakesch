-- AlterTable
ALTER TABLE "Project" ADD COLUMN     "branches_geojson" TEXT NOT NULL DEFAULT '',
ADD COLUMN     "cummulative_channel_length" DOUBLE PRECISION NOT NULL DEFAULT 0;
