/*
  Warnings:

  - You are about to drop the column `moFliesszeitId` on the `Project` table. All the data in the column will be lost.
  - A unique constraint covering the columns `[project_id]` on the table `Mod_Fliesszeit` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `project_id` to the `Mod_Fliesszeit` table without a default value. This is not possible if the table is not empty.

*/
-- DropForeignKey
ALTER TABLE "Project" DROP CONSTRAINT "Project_moFliesszeitId_fkey";

-- AlterTable
ALTER TABLE "Mod_Fliesszeit" ADD COLUMN     "project_id" TEXT NOT NULL;

-- AlterTable
ALTER TABLE "Project" DROP COLUMN "moFliesszeitId";

-- CreateIndex
CREATE UNIQUE INDEX "Mod_Fliesszeit_project_id_key" ON "Mod_Fliesszeit"("project_id");

-- AddForeignKey
ALTER TABLE "Mod_Fliesszeit" ADD CONSTRAINT "Mod_Fliesszeit_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
