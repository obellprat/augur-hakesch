/*
  Warnings:

  - The primary key for the `Project` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - Added the required column `description` to the `Project` table without a default value. This is not possible if the table is not empty.
  - Added the required column `lastModified` to the `Project` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "Project" DROP CONSTRAINT "Project_pkey",
ADD COLUMN     "description" TEXT NOT NULL,
ADD COLUMN     "lastModified" TIMESTAMP(3) NOT NULL,
ALTER COLUMN "id" DROP DEFAULT,
ALTER COLUMN "id" SET DATA TYPE TEXT,
ADD CONSTRAINT "Project_pkey" PRIMARY KEY ("id");
DROP SEQUENCE "Project_id_seq";
