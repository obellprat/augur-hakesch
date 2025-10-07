-- AlterTable
ALTER TABLE "NAM" ADD COLUMN     "readiness_to_drain" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "use_own_soil_data" BOOLEAN NOT NULL DEFAULT false;
