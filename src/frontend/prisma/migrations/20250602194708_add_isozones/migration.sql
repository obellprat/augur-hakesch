-- DropForeignKey
ALTER TABLE "Project" DROP CONSTRAINT "Project_pointId_fkey";

-- AlterTable
ALTER TABLE "Project" ADD COLUMN     "catchment_geojson" TEXT NOT NULL DEFAULT '',
ADD COLUMN     "isozones_running" TEXT NOT NULL DEFAULT '',
ADD COLUMN     "isozones_taskid" TEXT NOT NULL DEFAULT '';

-- AddForeignKey
ALTER TABLE "Project" ADD CONSTRAINT "Project_pointId_fkey" FOREIGN KEY ("pointId") REFERENCES "Point"("id") ON DELETE CASCADE ON UPDATE CASCADE;
